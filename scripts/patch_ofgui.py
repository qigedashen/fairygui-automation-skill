#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 @openfairygui/cli 的发布器补两处与 FairyGUI 官方编辑器不一致的行为：

1. 裁剪规则补上"根可达闭包"。
2. 让 FairyGUI 编辑器的 Lua 插件真正执行（fengari Lua 5.3）。

Lua 宿主依赖 fengari / fengari-interop，需与 @openfairygui/cli 同 node_modules 根：
    npm install fengari fengari-interop

用法：python patch_ofgui.py [dist_dir]
补丁可重复执行，已打过跳过。
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

NODE_OLD = """\t\tif (!manifest.main) {
\t\t\tconst error = /* @__PURE__ */ new Error(`Codegen plugin \"${manifest.name}\" is missing package.json main.`);
\t\t\tif (manifest.required) throw error;
\t\t\tdoc.getLogger().warn(`publish: Plugin \"${manifest.name}\" was skipped: ${error.message}`);
\t\t\tcontinue;
\t\t}
"""
NODE_SKIP = """\t\tif (/\\.lua$/iu.test(manifest.main)) {
\t\t\tdoc.getLogger().warn(`publish: Plugin \"${manifest.name}\" was skipped: FairyGUI editor Lua plugins are not supported`);
\t\t\tcontinue;
\t\t}
"""
NODE_LOADER = """\t\tif (/\\.lua$/iu.test(manifest.main)) {
\t\t\tconst luaMainPath = resolvePluginMain(path, pluginDir, manifest);
\t\t\ttry {
\t\t\t\tconst luaHost = await loadLuaPluginHost();
\t\t\t\tconst plugin = await luaHost.createLuaPlugin({ mainPath: luaMainPath, pluginDir, doc, manifest });
\t\t\t\tplugins.push({ name: manifest.name, plugin, failureMode: manifest.required ? \"abort\" : manifest.failureMode });
\t\t\t} catch (error) {
\t\t\t\tif (!manifest.required && manifest.failureMode === \"warn\") {
\t\t\t\t\tdoc.getLogger().warn(`publish: Plugin \"${manifest.name}\" was skipped: ${formatPluginError(error)}`);
\t\t\t\t\tcontinue;
\t\t\t\t}
\t\t\t\tthrow new Error(`publish: Failed to load Lua plugin \"${manifest.name}\": ${formatPluginError(error)}`);
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
    for dp, _dn, fns in os.walk(root):
        for n in fns:
            if re.match(r"^publish-.+\.(cjs|js|mjs)$", n): found.append(os.path.join(dp, n))
    return sorted(found)


def find_node_adapters(root):
    found = []
    for dp, _dn, fns in os.walk(root):
        for n in fns:
            if n in ("node.js", "node.cjs", "node.mjs"): found.append(os.path.join(dp, n))
    return sorted(found)


def resolve_root(arg):
    cands = []
    if arg: cands.append(arg)
    tmp = os.environ.get("TEMP") or os.environ.get("TMP") or ""
    if tmp: cands.append(os.path.join(tmp, "ofgui_test", "node_modules"))
    cands.append(os.path.join(os.getcwd(), "node_modules"))
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(os.path.dirname(os.path.dirname(here)), "node_modules"))
    for c in cands:
        d = os.path.join(c, "@openfairygui", "functions", "dist")
        if os.path.isdir(d): return d
        if os.path.basename(os.path.normpath(c)) == "dist" and os.path.isdir(c): return c
    return None


def patch_file(p):
    t = open(p, encoding="utf-8").read()
    if MARKER in t: return "skipped"
    if t.count(ANCHOR) != 1 or t.count(OLD_A) != 1 or t.count(OLD_C) != 1: return "anchor-mismatch"
    t = t.replace(ANCHOR, HELPER, 1).replace(OLD_A, NEW_A, 1).replace(OLD_C, NEW_C, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(t)
    return "patched"


def patch_node_adapter(p):
    t = open(p, encoding="utf-8").read()
    if LUA_HOST_MARKER in t: return "skipped"
    if t.count(LOAD_PLUGINS_ANCHOR) != 1: return "anchor-mismatch"
    helper = HOST_HELPER_CJS if p.endswith(".cjs") else HOST_HELPER_ESM
    t = t.replace(LOAD_PLUGINS_ANCHOR, helper, 1)
    if t.count(NODE_SKIP) == 1: t = t.replace(NODE_SKIP, NODE_LOADER, 1)
    elif t.count(NODE_OLD) == 1: t = t.replace(NODE_OLD, NODE_OLD + NODE_LOADER, 1)
    else: return "anchor-mismatch"
    open(p, "w", encoding="utf-8", newline="\n").write(t)
    return "patched"


def copy_lua_host(dist):
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "lua-plugin-host.cjs")
    if not os.path.isfile(src): print("ERROR: lua-plugin-host.cjs not found"); return "missing"
    tgt = os.path.join(dist, "lua-plugin-host.cjs")
    data = open(src, "rb").read()
    if os.path.isfile(tgt) and open(tgt, "rb").read() == data: return "skipped"
    open(tgt, "wb").write(data)
    return "copied"


def has_fengari(dist):
    m = os.path.normpath(os.path.join(dist, "..", "..", ".."))
    return os.path.isdir(os.path.join(m, "fengari")) and os.path.isdir(os.path.join(m, "fengari-interop"))


def main():
    dist = resolve_root(sys.argv[1] if len(sys.argv) > 1 else None)
    if not dist: print("ERROR: dist not found"); return 1
    print("target:", dist)
    bundles = find_publish_bundles(dist)
    if not bundles: print("ERROR: no publish-*.js"); return 1
    results = {}
    for p in bundles: results[p] = patch_file(p); print("%-9s %s" % (results[p], os.path.basename(p)))
    for p in find_node_adapters(dist): results[p] = patch_node_adapter(p); print("%-9s %s" % (results[p], os.path.basename(p)))
    print("%-9s %s" % (copy_lua_host(dist), "lua-plugin-host.cjs"))
    if not has_fengari(dist): print("WARN: fengari missing -> npm install fengari fengari-interop")
    bad = [p for p, v in results.items() if v == "anchor-mismatch"]
    if bad: print("ERROR: anchor-mismatch:", bad); return 1
    return 0

if __name__ == "__main__": sys.exit(main())
