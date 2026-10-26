#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 @openfairygui/cli 的发布器补两处与 FairyGUI 官方编辑器不一致的行为：

1. 裁剪规则补上"根可达闭包"。

背景：ofgui 发布时只判断"资源被任意组件引用即保留"，导致仅被"不可达组件"引用的
图片仍会打进包/图集，产物与 FairyGUI 官方编辑器不一致。

官方规则（对 Bag 包 107 项全量验证，零误差）：
    发布集 = exported="true" 的项（根，图片也可 exported）
             ∪ 从根出发沿组件子项引用（src / ui:// URL / list 项 / gear 等）的可达闭包
             ∪ 字体纹理与骨骼依赖（沿用原 collectExportedResourceIds）

2. 让 FairyGUI 编辑器的 Lua 插件真正执行。

ofgui 只支持 JS Codegen 插件，遇到 plugins/<name>/main.lua 会跳过。补丁会把
tools/ofgui_lua/lua-plugin-host.cjs 复制进 dist，并让插件加载器用 fengari 跑这些
Lua 插件（暴露 PluginPath / App / CS / fprint / require 与 onPublishStart 等钩子）。
Lua 侧对 item.exported 的赋值会直接写回 ofgui 的 Resource，因此像 996Extend 的
ItemIcon 过滤这类插件能真正改变发布集。

Lua 宿主依赖 fengari / fengari-interop，需与 @openfairygui/cli 装在同一个
node_modules 根目录：npm install fengari fengari-interop

用法：
    python tools\\ofgui_patch\\patch_ofgui.py [@openfairygui/functions/dist 目录]
不传参数时依次尝试：%TEMP%\\ofgui_test\\node_modules、当前目录 node_modules、
脚本所在仓库根目录 node_modules。

补丁可重复执行；已打过补丁的文件会跳过。
"""

import os
import re
import sys

ANCHOR = "function collectPackagePublishContext(pkg, options) {"

MARKER = "collectRootReachableResourceIds"

HELPER = """function collectRootReachableResourceIds(pkg, excludedResourceIds, seedIds) {
\tconst resources = pkg.listResources();
\tconst resourceById = /* @__PURE__ */ new Map(resources.map((resource) => [resource.getId(), resource]));
\tconst included = /* @__PURE__ */ new Set();
\tconst queue = [];
\tconst addId = (resourceId) => {
\t\tif (!resourceId || included.has(resourceId) || excludedResourceIds.has(resourceId)) return;
\t\tconst resource = resourceById.get(resourceId);
\t\tif (!resource) return;
\t\tif (isFontResource(resource) && resource.isExternalFont()) return;
\t\tincluded.add(resourceId);
\t\tqueue.push(resourceId);
\t};
\tfor (const resource of resources) if (resource.getExported()) addId(resource.getId());
\tfor (const resourceId of seedIds ?? []) addId(resourceId);
\twhile (queue.length > 0) {
\t\tconst resource = resourceById.get(queue.pop());
\t\tif (!resource) continue;
\t\tif (isComponentResource(resource)) {
\t\t\tconst dependencies = { localResourceIds: /* @__PURE__ */ new Set(), packageIds: /* @__PURE__ */ new Set() };
\t\t\tcollectComponentReferences(dependencies, pkg.getId(), resource);
\t\t\tfor (const resourceId of dependencies.localResourceIds) addId(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (isSkeletonResource(resource)) {
\t\t\tfor (const requiredId of resource.getRequireIds()) addId(requiredId);
\t\t\tcontinue;
\t\t}
\t\tif (isFontResource(resource)) for (const imageId of getFontDependencyImageIds(resource)) addId(imageId);
\t}
\treturn included;
}
function collectPackagePublishContext(pkg, options) {"""

# 包内 item 表的裁剪规则
OLD_A = """\tconst publishedResourceIds = /* @__PURE__ */ new Set();
\tfor (const resource of resources) {
\t\tconst resourceId = resource.getId();
\t\tif (!resourceId || excludedResourceIds.has(resourceId)) continue;
\t\tif (isComponentResource(resource)) {
\t\t\tif (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (isImageResource(resource)) {
\t\t\tif (resource.getExported() || referencedIds.has(resourceId) || pixelHitTestImageIds.has(resourceId)) publishedResourceIds.add(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (isMovieClipResource(resource) || isSoundResource(resource)) {
\t\t\tif (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (isMiscResource(resource) || isSkeletonResource(resource)) {
\t\t\tif (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (isFontResource(resource)) {
\t\t\tif (!resource.isExternalFont() && (resource.getExported() || referencedIds.has(resourceId))) publishedResourceIds.add(resourceId);
\t\t\tcontinue;
\t\t}
\t\tif (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
\t}
"""

NEW_A = """\tconst publishedResourceIds = collectRootReachableResourceIds(pkg, excludedResourceIds, pixelHitTestImageIds);
"""

# 图集收集时的兜底裁剪规则
OLD_C = """\t\t\tconst referencedIds = collectPackageResourceReferences(pkg).localResourceIds;
\t\t\tfor (const res of orderedAllResources) {
\t\t\t\tif (isSkeletonResource(res) && referencedIds.has(res.getId())) {
\t\t\t\t\tfor (const requiredId of res.getRequireIds()) if (requiredId) referencedIds.add(requiredId);
\t\t\t\t}
\t\t\t\tif (isFontResource(res)) for (const imageId of getFontDependencyImageIds(res)) referencedIds.add(imageId);
\t\t\t}
"""

NEW_C = """\t\t\tconst referencedIds = collectRootReachableResourceIds(pkg, new Set(pkg.getSourceAtlasSettings().excludedResourceIds));
"""

# 插件加载：让 FairyGUI 编辑器的 Lua 插件（plugins/<name>/main.lua）真正执行，
# 而不是直接跳过。宿主由 tools/ofgui_lua/lua-plugin-host.cjs 提供，会被复制到 dist 下。
NODE_OLD = """\t\tif (!manifest.main) {
\t\t\tconst error = /* @__PURE__ */ new Error(`Codegen plugin "${manifest.name}" is missing package.json main.`);
\t\t\tif (manifest.required) throw error;
\t\t\tdoc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: ${error.message}`);
\t\t\tcontinue;
\t\t}
"""

# 上一版补丁（只跳过 Lua 插件），需要在升级时替换掉
NODE_SKIP = """\t\tif (/\\.lua$/iu.test(manifest.main)) {
\t\t\tdoc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: FairyGUI editor Lua plugins are not supported`);
\t\t\tcontinue;
\t\t}
"""

NODE_LOADER = """\t\tif (/\\.lua$/iu.test(manifest.main)) {
\t\t\tconst luaMainPath = resolvePluginMain(path, pluginDir, manifest);
\t\t\ttry {
\t\t\t\tconst luaHost = await loadLuaPluginHost();
\t\t\t\tconst plugin = await luaHost.createLuaPlugin({ mainPath: luaMainPath, pluginDir, doc, manifest });
\t\t\t\tplugins.push({
\t\t\t\t\tname: manifest.name,
\t\t\t\t\tplugin,
\t\t\t\t\tfailureMode: manifest.required ? "abort" : manifest.failureMode
\t\t\t\t});
\t\t\t} catch (error) {
\t\t\t\tif (!manifest.required && manifest.failureMode === "warn") {
\t\t\t\t\tdoc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: ${formatPluginError(error)}`);
\t\t\t\t\tcontinue;
\t\t\t\t}
\t\t\t\tthrow new Error(`publish: Failed to load Lua plugin "${manifest.name}": ${formatPluginError(error)}`);
\t\t\t}
\t\t\tcontinue;
\t\t}
"""

LOAD_PLUGINS_ANCHOR = "async function loadPlugins(doc, pluginsDir) {"

LUA_HOST_MARKER = "lua-plugin-host.cjs"

HOST_HELPER_ESM = """async function loadLuaPluginHost() {
\tconst mod = await import(new URL("./lua-plugin-host.cjs", import.meta.url).href);
\treturn mod.default ?? mod;
}
async function loadPlugins(doc, pluginsDir) {"""

HOST_HELPER_CJS = """function loadLuaPluginHost() {
\treturn require("./lua-plugin-host.cjs");
}
async function loadPlugins(doc, pluginsDir) {"""


def find_publish_bundles(root):
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if re.match(r"^publish-.+\.(cjs|js|mjs)$", name):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def find_node_adapter_bundles(root):
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name in ("node.js", "node.cjs", "node.mjs"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def resolve_root(arg):
    candidates = []
    if arg:
        candidates.append(arg)
    temp = os.environ.get("TEMP") or os.environ.get("TMP") or ""
    if temp:
        candidates.append(os.path.join(temp, "ofgui_test", "node_modules"))
    candidates.append(os.path.join(os.getcwd(), "node_modules"))
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    candidates.append(os.path.join(repo, "node_modules"))
    for cand in candidates:
        dist = os.path.join(cand, "@openfairygui", "functions", "dist")
        if os.path.isdir(dist):
            return dist
        if os.path.basename(os.path.normpath(cand)) == "dist" and os.path.isdir(cand):
            return cand
    return None


def patch_file(path):
    text = open(path, encoding="utf-8").read()
    if MARKER in text:
        return "skipped"
    if text.count(ANCHOR) != 1 or text.count(OLD_A) != 1 or text.count(OLD_C) != 1:
        return "anchor-mismatch"
    text = text.replace(ANCHOR, HELPER, 1)
    text = text.replace(OLD_A, NEW_A, 1)
    text = text.replace(OLD_C, NEW_C, 1)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    return "patched"


def patch_node_adapter(path):
    text = open(path, encoding="utf-8").read()
    if LUA_HOST_MARKER in text:
        return "skipped"
    if text.count(LOAD_PLUGINS_ANCHOR) != 1:
        return "anchor-mismatch"
    helper = HOST_HELPER_CJS if path.endswith(".cjs") else HOST_HELPER_ESM
    text = text.replace(LOAD_PLUGINS_ANCHOR, helper, 1)
    if text.count(NODE_SKIP) == 1:
        text = text.replace(NODE_SKIP, NODE_LOADER, 1)
    elif text.count(NODE_OLD) == 1:
        text = text.replace(NODE_OLD, NODE_OLD + NODE_LOADER, 1)
    else:
        return "anchor-mismatch"
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    return "patched"


def copy_lua_host(dist):
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "lua-plugin-host.cjs")
    if not os.path.isfile(source):
        print("ERROR: Lua plugin host not found:", source)
        return "missing"
    target = os.path.join(dist, "lua-plugin-host.cjs")
    with open(source, "rb") as handle:
        data = handle.read()
    if os.path.isfile(target):
        with open(target, "rb") as handle:
            if handle.read() == data:
                return "skipped"
    with open(target, "wb") as handle:
        handle.write(data)
    return "copied"


def has_fengari(dist):
    modules = os.path.normpath(os.path.join(dist, "..", "..", ".."))
    return os.path.isdir(os.path.join(modules, "fengari")) and os.path.isdir(
        os.path.join(modules, "fengari-interop")
    )


def main():
    dist = resolve_root(sys.argv[1] if len(sys.argv) > 1 else None)
    if not dist:
        print("ERROR: 未找到 @openfairygui/functions/dist，请显式传入 node_modules 或 dist 路径")
        return 1
    print("target:", dist)
    bundles = find_publish_bundles(dist)
    if not bundles:
        print("ERROR: 目录下没有 publish-*.js 发布器文件")
        return 1
    results = {}
    for path in bundles:
        results[path] = patch_file(path)
        print("%-9s %s" % (results[path], os.path.basename(path)))
    adapters = find_node_adapter_bundles(dist)
    if not adapters:
        print("WARN: 未找到 node.js/node.cjs 插件加载适配器，Lua 插件补丁未应用")
    for path in adapters:
        results[path] = patch_node_adapter(path)
        print("%-9s %s" % (results[path], os.path.basename(path)))
    host_result = copy_lua_host(dist)
    print("%-9s %s" % (host_result, "lua-plugin-host.cjs"))
    if host_result == "missing":
        return 1
    if not has_fengari(dist):
        print("WARN: 该安装目录缺少 fengari / fengari-interop，Lua 插件会在加载时报错。")
        print("      请在同一 node_modules 根目录执行：npm install fengari fengari-interop")
    mismatched = [p for p, v in results.items() if v == "anchor-mismatch"]
    if mismatched:
        print("ERROR: 以下文件未匹配补丁锚点（ofgui 版本可能已变更，需要重新核对逻辑）：")
        for path in mismatched:
            print("  ", path)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
