#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys

ANCHOR = "function collectPackagePublishContext(pkg, options) {"
MARKER = "collectRootReachableResourceIds"

HELPER = """function collectRootReachableResourceIds(pkg, excludedResourceIds, seedIds) {
	const resources = pkg.listResources();
	const resourceById = /* @__PURE__ */ new Map(resources.map((resource) => [resource.getId(), resource]));
	const included = /* @__PURE__ */ new Set();
	const queue = [];
	const addId = (resourceId) => {
		if (!resourceId || included.has(resourceId) || excludedResourceIds.has(resourceId)) return;
		const resource = resourceById.get(resourceId);
		if (!resource) return;
		if (isFontResource(resource) && resource.isExternalFont()) return;
		included.add(resourceId);
		queue.push(resourceId);
	};
	for (const resource of resources) if (resource.getExported()) addId(resource.getId());
	for (const resourceId of seedIds ?? []) addId(resourceId);
	while (queue.length > 0) {
		const resource = resourceById.get(queue.pop());
		if (!resource) continue;
		if (isComponentResource(resource)) {
			const dependencies = { localResourceIds: /* @__PURE__ */ new Set(), packageIds: /* @__PURE__ */ new Set() };
			collectComponentReferences(dependencies, pkg.getId(), resource);
			for (const resourceId of dependencies.localResourceIds) addId(resourceId);
			continue;
		}
		if (isSkeletonResource(resource)) {
			for (const requiredId of resource.getRequireIds()) addId(requiredId);
			continue;
		}
		if (isFontResource(resource)) for (const imageId of getFontDependencyImageIds(resource)) addId(imageId);
	}
	return included;
}
function collectPackagePublishContext(pkg, options) {"""

OLD_A = """	const publishedResourceIds = /* @__PURE__ */ new Set();
	for (const resource of resources) {
		const resourceId = resource.getId();
		if (!resourceId || excludedResourceIds.has(resourceId)) continue;
		if (isComponentResource(resource)) {
			if (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
			continue;
		}
		if (isImageResource(resource)) {
			if (resource.getExported() || referencedIds.has(resourceId) || pixelHitTestImageIds.has(resourceId)) publishedResourceIds.add(resourceId);
			continue;
		}
		if (isMovieClipResource(resource) || isSoundResource(resource)) {
			if (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
			continue;
		}
		if (isMiscResource(resource) || isSkeletonResource(resource)) {
			if (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
			continue;
		}
		if (isFontResource(resource)) {
			if (!resource.isExternalFont() && (resource.getExported() || referencedIds.has(resourceId))) publishedResourceIds.add(resourceId);
			continue;
		}
		if (resource.getExported() || referencedIds.has(resourceId)) publishedResourceIds.add(resourceId);
	}
"""
NEW_A = """	const publishedResourceIds = collectRootReachableResourceIds(pkg, excludedResourceIds, pixelHitTestImageIds);
"""

OLD_C = """			const referencedIds = collectPackageResourceReferences(pkg).localResourceIds;
			for (const res of orderedAllResources) {
				if (isSkeletonResource(res) && referencedIds.has(res.getId())) {
					for (const requiredId of res.getRequireIds()) if (requiredId) referencedIds.add(requiredId);
				}
				if (isFontResource(res)) for (const imageId of getFontDependencyImageIds(res)) referencedIds.add(imageId);
			}
"""
NEW_C = """			const referencedIds = collectRootReachableResourceIds(pkg, new Set(pkg.getSourceAtlasSettings().excludedResourceIds));
"""

NODE_OLD = """		if (!manifest.main) {
			const error = /* @__PURE__ */ new Error(`Codegen plugin "${manifest.name}" is missing package.json main.`);
			if (manifest.required) throw error;
			doc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: ${error.message}`);
			continue;
		}
"""
NODE_SKIP = """		if (/\.lua$/iu.test(manifest.main)) {
			doc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: FairyGUI editor Lua plugins are not supported`);
			continue;
		}
"""
NODE_LOADER = """		if (/\.lua$/iu.test(manifest.main)) {
			const luaMainPath = resolvePluginMain(path, pluginDir, manifest);
			try {
				const luaHost = await loadLuaPluginHost();
				const plugin = await luaHost.createLuaPlugin({ mainPath: luaMainPath, pluginDir, doc, manifest });
				plugins.push({ name: manifest.name, plugin, failureMode: manifest.required ? "abort" : manifest.failureMode });
			} catch (error) {
				if (!manifest.required && manifest.failureMode === "warn") {
					doc.getLogger().warn(`publish: Plugin "${manifest.name}" was skipped: ${formatPluginError(error)}`);
					continue;
				}
				throw new Error(`publish: Failed to load Lua plugin "${manifest.name}": ${formatPluginError(error)}`);
			}
			continue;
		}
"""

LOAD_PLUGINS_ANCHOR = "async function loadPlugins(doc, pluginsDir) {"
LUA_HOST_MARKER = "lua-plugin-host.cjs"
HOST_HELPER_ESM = """async function loadLuaPluginHost() {
	const mod = await import(new URL("./lua-plugin-host.cjs", import.meta.url).href);
	return mod.default ?? mod;
}
async function loadPlugins(doc, pluginsDir) {"""
HOST_HELPER_CJS = """function loadLuaPluginHost() {
	return require("./lua-plugin-host.cjs");
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
