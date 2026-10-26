"use strict";
/**
 * FairyGUI 编辑器 Lua 插件宿主（供 ofgui publish 调用）。
 *
 * fengari 执行 Lua 插件，暴露 PluginPath / App / CS / fprint / require
 * 与 onPublishStart / onPublishEnd / onDestroy 钩子。Lua 侧 item.exported
 * 会直接写回 ofgui 的 Resource。
 *
 * 依赖: fengari, fengari-interop（同 node_modules 根）。
 */

const fs = require("node:fs");
const path = require("node:path");
const { lua, lauxlib, lualib, to_luastring, to_jsstring } = require("fengari");
const interop = require("fengari-interop");

const IMAGE_EXT_RE = /\.(png|jpe?g|gif|bmp|webp|jta|swf|mp3|wav|fnt|xml|json|bin|bytes)$/iu;

function isFile(p) { try { return fs.statSync(p).isFile(); } catch { return false; } }
function luaErrorText(L) { const v = lua.lua_tostring(L, -1); const s = v === null ? "unknown" : to_jsstring(v); lua.lua_pop(L, 1); return s; }
function pcallChecked(L, n, r) { const st = lua.lua_pcall(L, n, r, 0); if (st !== lua.LUA_OK) throw new Error(luaErrorText(L)); }
function editorItemName(res) { const raw = (typeof res.getName === "function" ? res.getName() : "") || ""; return raw.replace(IMAGE_EXT_RE, ""); }

function createPrefs(pluginDir, logger) {
    const prefsFile = path.join(pluginDir, "ofgui-prefs.json");
    let data = {};
    try { data = JSON.parse(fs.readFileSync(prefsFile, "utf-8")); } catch { data = {}; }
    const envName = (k) => `OFGUI_${String(k).toUpperCase().replace(/[^A-Z0-9]/gu, "_")}`;
    return {
        get(key) {
            const e = process.env[envName(key)]; if (e !== undefined) return e;
            const v = data[key]; return typeof v === "string" ? v : "";
        },
        set(key, value) {
            data[key] = value;
            try { fs.writeFileSync(prefsFile, JSON.stringify(data, null, 2), "utf-8"); }
            catch (err) { logger.warn(`publish: [lua plugin] prefs persist failed: ${err.message}`); }
        }
    };
}

function buildItem(res) {
    return {
        get name() { return editorItemName(res); },
        get exported() { return typeof res.getExported === "function" ? !!res.getExported() : false; },
        set exported(v) { if (typeof res.setExported === "function") res.setExported(!!v); },
        get id() { return typeof res.getId === "function" ? res.getId() : ""; },
        get path() { return typeof res.getPath === "function" ? res.getPath() || "/" : "/"; }
    };
}

function buildItems(pkg) {
    const items = {};
    const resources = typeof pkg.listResources === "function" ? pkg.listResources() : [];
    resources.forEach((res, i) => { items[i] = buildItem(res); });
    return items;
}

class LuaPluginRuntime {
    constructor(options) {
        this.mainPath = options.mainPath;
        this.pluginDir = options.pluginDir;
        this.doc = options.doc;
        this.logger = options.doc.getLogger();
        this.pluginName = options.manifest?.name || path.basename(options.pluginDir);
        this.projectDir = this.doc.getProjectDir?.() || path.resolve(options.pluginDir, "..", "..");
        this.prefs = createPrefs(this.pluginDir, this.logger);
        this.moduleRefs = new Map();
        this.loadingModules = new Set();
        this.L = lauxlib.luaL_newstate();
        lualib.luaL_openlibs(this.L);
        interop.luaopen_js(this.L);
        this.installGlobals();
    }

    setGlobalValue(n, v) { interop.push(this.L, v); lua.lua_setglobal(this.L, to_luastring(n)); }
    setGlobalFunction(n, fn) { lua.lua_pushcfunction(this.L, fn); lua.lua_setglobal(this.L, to_luastring(n)); }

    installGlobals() {
        this.setGlobalValue("PluginPath", this.pluginDir);
        this.setGlobalValue("App", this.createApp());
        this.setGlobalValue("CS", this.createUnityStubs());
        this.setGlobalFunction("fprint", (L) => {
            const count = lua.lua_gettop(L); const parts = [];
            for (let i = 1; i <= count; i++) {
                const v = lua.lua_tostring(L, i); parts.push(v === null ? "nil" : to_jsstring(v));
            }
            this.logger.info(`[${this.pluginName}] ${parts.join("\t")}`); return 0;
        });
        this.setGlobalFunction("require", (L) => this.luaRequire(L));
    }

    createUnityStubs() {
        const prefs = this.prefs;
        return {
            FairyGUI: { UIPackage: { CreateObject: () => null } },
            UnityEngine: {
                PlayerPrefs: {
                    GetString(key) { const a = typeof key === "string" ? key : typeof this === "string" ? this : ""; return prefs.get(a); },
                    SetString(key, value) {
                        const k = typeof key === "string" && value !== undefined ? key : String(this);
                        const v = typeof key === "string" && value !== undefined ? value : key;
                        prefs.set(k, String(v));
                    },
                    Save: () => {}
                }
            }
        };
    }

    createApp() {
        const logger = this.logger, pluginName = this.pluginName, noop = () => {};
        const alert = function (msg) { const a = msg !== undefined ? msg : this; logger.warn(`publish: [${pluginName}] ${a}`); };
        const sm = { AddItem: noop, RemoveItem: noop, GetSubMenu: () => sm };
        return {
            project: { basePath: this.projectDir, GetSettings: (name) => {
                const s = this.doc.getRoot().getSettings?.() ?? {};
                return name ? (s[name] ?? s[String(name).toLowerCase()] ?? {}) : s;
            }},
            menu: sm, groot: { width: 1280, height: 720, AddChild: noop },
            libView: { contextMenu: sm, GetSelectedResource: () => null, SetResourcesExported: noop },
            inspectorView: { AddInspector: noop }, docFactory: { ConnectInspector: noop },
            pluginManager: { LoadUIPackage: (p) => logger.info(`publish: [${pluginName}] package ignored in CLI: ${p}`) },
            activeDoc: null, Alert: alert, alert: alert
        };
    }

    resolveModule(name) {
        const norm = String(name).replace(/\//gu, path.sep);
        const cands = [];
        const push = (base) => { cands.push(base, `${base}.lua`, path.join(base, "init.lua")); };
        if (path.isAbsolute(norm)) push(norm);
        else {
            push(path.resolve(this.pluginDir, norm));
            push(path.resolve(this.projectDir, norm));
            push(path.resolve(this.projectDir, "..", norm));
            push(path.resolve(process.cwd(), norm));
        }
        return cands.find(isFile) ?? null;
    }

    loadChunk(buf, name) {
        const bytes = buf instanceof Uint8Array ? buf : Buffer.from(String(buf), "utf-8");
        const st = lauxlib.luaL_loadbuffer(this.L, bytes, bytes.length, to_luastring(name));
        if (st !== lua.LUA_OK) throw new Error(`${name}: ${luaErrorText(this.L)}`);
    }

    luaRequire(L) {
        const name = to_jsstring(lauxlib.luaL_checkstring(L, 1));
        const cached = this.moduleRefs.get(name);
        if (cached !== undefined) { lua.lua_rawgeti(L, lua.LUA_REGISTRYINDEX, cached); return 1; }
        const fp = this.resolveModule(name);
        if (!fp) { this.logger.warn(`publish: [${this.pluginName}] require("${name}") not found`); lua.lua_pushstring(L, to_luastring(`module '${name}' not found`)); lua.lua_error(L); return 0; }
        if (this.loadingModules.has(fp)) { lua.lua_pushstring(L, to_luastring(`loop loading '${name}'`)); lua.lua_error(L); return 0; }
        this.loadingModules.add(fp);
        try {
            this.loadChunk(fs.readFileSync(fp), `@${fp}`); pcallChecked(L, 0, 1);
            if (lua.lua_type(L, -1) === lua.LUA_TNIL) { lua.lua_pop(L, 1); lua.lua_pushboolean(L, true); }
            const ref = lauxlib.luaL_ref(L, lua.LUA_REGISTRYINDEX);
            this.moduleRefs.set(name, ref); lua.lua_rawgeti(L, lua.LUA_REGISTRYINDEX, ref); return 1;
        } catch (err) {
            this.logger.warn(`publish: [${this.pluginName}] require("${name}") failed: ${err.message}`);
            lua.lua_pushstring(L, to_luastring(`error loading '${name}': ${err.message}`)); lua.lua_error(L); return 0;
        } finally { this.loadingModules.delete(fp); }
    }

    loadMain() {
        if (!isFile(this.mainPath)) throw new Error(`Lua plugin entry not found: ${this.mainPath}`);
        this.loadChunk(fs.readFileSync(this.mainPath), `@${this.mainPath}`); pcallChecked(this.L, 0, 0);
    }

    buildPackages() {
        const root = this.doc.getRoot();
        const packages = (typeof root.listPackages === "function" ? root.listPackages() : []).map((pkg) => ({
            name: pkg.getName(),
            id: typeof pkg.getId === "function" ? pkg.getId() : "",
            items: buildItems(pkg)
        }));
        packages.Length = packages.length;
        return packages;
    }

    callGlobal(hook, args) {
        lua.lua_getglobal(this.L, to_luastring(hook));
        if (lua.lua_type(this.L, -1) !== lua.LUA_TFUNCTION) { lua.lua_pop(this.L, 1); return false; }
        for (const a of args) interop.push(this.L, a);
        pcallChecked(this.L, args.length, 0); return true;
    }

    createHooks() {
        return {
            onPublishStart: () => {
                const before = this.countExported();
                if (!this.callGlobal("onPublishStart", [this.buildPackages()])) return;
                for (const [n, c] of this.countExported()) {
                    const prev = before.get(n);
                    if (prev !== undefined && prev !== c) this.logger.info(`publish: [${this.pluginName}] ${n}: exported ${prev} -> ${c}`);
                }
                this.logger.info(`publish: [${this.pluginName}] onPublishStart handled by Lua`);
            },
            onPublishEnd: () => { this.callGlobal("onPublishEnd", [this.buildPackages()]); },
            onDestroy: () => { this.callGlobal("onDestroy", []); }
        };
    }

    countExported() {
        const counts = new Map();
        const pkgs = typeof this.doc.getRoot().listPackages === "function" ? this.doc.getRoot().listPackages() : [];
        for (const pkg of pkgs) {
            const res = typeof pkg.listResources === "function" ? pkg.listResources() : [];
            counts.set(pkg.getName(), res.filter((r) => r.getExported?.()).length);
        }
        return counts;
    }
}

async function createLuaPlugin(options) {
    const runtime = new LuaPluginRuntime(options);
    runtime.loadMain();
    return runtime.createHooks();
}

module.exports = { createLuaPlugin };
