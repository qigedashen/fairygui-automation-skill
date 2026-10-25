"use strict";
/**
 * FairyGUI 编辑器 Lua 插件宿主（供 ofgui publish 的插件加载器调用）。
 *
 * ofgui 原生只支持 JS Codegen 插件，遇到 plugins/<name>/main.lua 会直接跳过。
 * 本宿主用 fengari（纯 JS 的 Lua 5.3 运行时）执行这些 Lua 插件，并按 FairyGUI
 * 编辑器的约定暴露最小可用环境：
 *   - 全局 PluginPath / App / CS / fprint / require
 *   - 插件入口 main.lua 顶层的注册代码可以正常跑
 *   - 发布钩子 onPublishStart / onPublishEnd 会被映射到 ofgui 的发布流程
 *
 * 关键点：App / CS / packages / package.items 都是 JS 对象代理，Lua 里
 * `item.exported = true` 这类赋值会直接写回 ofgui 的 Resource（setExported），
 * 因此插件对发布集的修改能真正生效。
 *
 * 依赖：fengari、fengari-interop（与 @openfairygui/cli 装在同一个 node_modules 根目录）。
 */

const fs = require("node:fs");
const path = require("node:path");
const { lua, lauxlib, lualib, to_luastring, to_jsstring } = require("fengari");
const interop = require("fengari-interop");

const IMAGE_EXT_RE = /\.(png|jpe?g|gif|bmp|webp|jta|swf|mp3|wav|fnt|xml|json|bin|bytes)$/iu;

function isFile(filePath) {
	try {
		return fs.statSync(filePath).isFile();
	} catch {
		return false;
	}
}

function luaErrorText(L) {
	const value = lua.lua_tostring(L, -1);
	const text = value === null ? "unknown Lua error" : to_jsstring(value);
	lua.lua_pop(L, 1);
	return text;
}

function raise(L, message) {
	lua.lua_pushstring(L, to_luastring(message));
	return lua.lua_error(L);
}

function pcallChecked(L, nargs, nresults) {
	const status = lua.lua_pcall(L, nargs, nresults, 0);
	if (status !== lua.LUA_OK) throw new Error(luaErrorText(L));
}

/** 资源名对齐 FairyGUI 编辑器：图片名不带扩展名（003410.png -> 003410）。 */
function editorItemName(resource) {
	const raw = (typeof resource.getName === "function" ? resource.getName() : "") || "";
	return raw.replace(IMAGE_EXT_RE, "");
}

function createPrefs(pluginDir, logger) {
	const prefsFile = path.join(pluginDir, "ofgui-prefs.json");
	let data = {};
	try {
		data = JSON.parse(fs.readFileSync(prefsFile, "utf-8"));
	} catch {
		data = {};
	}
	const envName = (key) => `OFGUI_${String(key).toUpperCase().replace(/[^A-Z0-9]/gu, "_")}`;
	return {
		/** 取值优先级：环境变量 > ofgui-prefs.json > 空串（与编辑器未配置时一致）。 */
		get(key) {
			const fromEnv = process.env[envName(key)];
			if (fromEnv !== undefined) return fromEnv;
			const value = data[key];
			return typeof value === "string" ? value : "";
		},
		set(key, value) {
			data[key] = value;
			try {
				fs.writeFileSync(prefsFile, JSON.stringify(data, null, 2), "utf-8");
			} catch (error) {
				logger.warn(`publish: [lua plugin] could not persist prefs "${key}": ${error.message}`);
			}
		}
	};
}

function buildItem(resource) {
	const item = {
		get name() {
			return editorItemName(resource);
		},
		get exported() {
			return typeof resource.getExported === "function" ? !!resource.getExported() : false;
		},
		set exported(value) {
			if (typeof resource.setExported === "function") resource.setExported(!!value);
		},
		get id() {
			return typeof resource.getId === "function" ? resource.getId() : "";
		},
		get path() {
			return typeof resource.getPath === "function" ? resource.getPath() || "/" : "/";
		}
	};
	Object.defineProperty(item, "__resource", { value: resource, enumerable: false });
	return item;
}

function buildItems(pkg) {
	const items = {};
	const resources = typeof pkg.listResources === "function" ? pkg.listResources() : [];
	resources.forEach((resource, index) => {
		items[index] = buildItem(resource);
	});
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

	setGlobalValue(name, value) {
		interop.push(this.L, value);
		lua.lua_setglobal(this.L, to_luastring(name));
	}

	setGlobalFunction(name, fn) {
		lua.lua_pushcfunction(this.L, fn);
		lua.lua_setglobal(this.L, to_luastring(name));
	}

	installGlobals() {
		this.setGlobalValue("PluginPath", this.pluginDir);
		this.setGlobalValue("App", this.createApp());
		this.setGlobalValue("CS", this.createUnityStubs());
		this.setGlobalFunction("fprint", (L) => {
			const count = lua.lua_gettop(L);
			const parts = [];
			for (let index = 1; index <= count; index += 1) {
				const value = lua.lua_tostring(L, index);
				parts.push(value === null ? "nil" : to_jsstring(value));
			}
			this.logger.info(`[${this.pluginName}] ${parts.join("\t")}`);
			return 0;
		});
		this.setGlobalFunction("require", (L) => this.luaRequire(L));
	}

	createUnityStubs() {
		// 注意：Lua 里 `CS.UnityEngine.PlayerPrefs.GetString(...)` 是点调用，
		// fengari-interop 会把第一个参数当成 this，所以这里要同时兼容点调用与冒号调用。
		const prefs = this.prefs;
		return {
			FairyGUI: {
				UIPackage: {
					CreateObject: () => null
				}
			},
			UnityEngine: {
				PlayerPrefs: {
					GetString(key) {
						const actual = typeof key === "string" ? key : typeof this === "string" ? this : "";
						return prefs.get(actual);
					},
					SetString(key, value) {
						const actualKey = typeof key === "string" && value !== undefined ? key : String(this);
						const actualValue = typeof key === "string" && value !== undefined ? value : key;
						prefs.set(actualKey, String(actualValue));
					},
					Save: () => {}
				}
			}
		};
	}

	createApp() {
		const logger = this.logger;
		const projectDir = this.projectDir;
		const pluginName = this.pluginName;
		const noop = () => {};
		// Lua 侧大量使用点调用 App.Alert("...")，第一个参数会被当成 this，这里做兼容
		const alert = function (message) {
			const actual = message !== undefined ? message : this;
			logger.warn(`publish: [${pluginName}] ${actual}`);
		};
		const stubMenu = {
			AddItem: noop,
			RemoveItem: noop,
			GetSubMenu: () => stubMenu
		};
		return {
			project: {
				basePath: projectDir,
				GetSettings: (name) => {
					const settings = this.doc.getRoot().getSettings?.() ?? {};
					if (!name) return settings;
					const key = String(name);
					return settings[key] ?? settings[key.toLowerCase()] ?? {};
				}
			},
			menu: stubMenu,
			groot: { width: 1280, height: 720, AddChild: noop },
			libView: {
				contextMenu: stubMenu,
				GetSelectedResource: () => null,
				// 编辑器里这是"批量设置导出标记"；Lua 侧已经直接写 item.exported，
				// 这里保持空实现即可（Lua 表参数无法无损转回 JS 数组）。
				SetResourcesExported: noop
			},
			inspectorView: { AddInspector: noop },
			docFactory: { ConnectInspector: noop },
			pluginManager: {
				LoadUIPackage: (pkgPath) => logger.info(`publish: [${pluginName}] UI package ignored in CLI: ${pkgPath}`)
			},
			activeDoc: null,
			Alert: alert,
			alert: alert
		};
	}

	resolveModule(name) {
		const normalized = String(name).replace(/\//gu, path.sep);
		const candidates = [];
		const pushCandidates = (base) => {
			candidates.push(base, `${base}.lua`, path.join(base, "init.lua"));
		};
		if (path.isAbsolute(normalized)) {
			pushCandidates(normalized);
		} else {
			pushCandidates(path.resolve(this.pluginDir, normalized));
			pushCandidates(path.resolve(this.projectDir, normalized));
			pushCandidates(path.resolve(this.projectDir, "..", normalized));
			pushCandidates(path.resolve(process.cwd(), normalized));
		}
		return candidates.find(isFile) ?? null;
	}

	loadChunk(buffer, chunkName) {
		const L = this.L;
		const bytes = buffer instanceof Uint8Array ? buffer : Buffer.from(String(buffer), "utf-8");
		const status = lauxlib.luaL_loadbuffer(L, bytes, bytes.length, to_luastring(chunkName));
		if (status !== lua.LUA_OK) throw new Error(`${chunkName}: ${luaErrorText(L)}`);
	}

	luaRequire(L) {
		const rawName = lauxlib.luaL_checkstring(L, 1);
		const name = to_jsstring(rawName);
		const cachedRef = this.moduleRefs.get(name);
		if (cachedRef !== undefined) {
			lua.lua_rawgeti(L, lua.LUA_REGISTRYINDEX, cachedRef);
			return 1;
		}
		const filePath = this.resolveModule(name);
		if (!filePath) {
			this.logger.warn(`publish: [${this.pluginName}] require("${name}") not found`);
			return raise(L, `module '${name}' not found`);
		}
		if (this.loadingModules.has(filePath)) return raise(L, `loop or previous error loading module '${name}'`);
		this.loadingModules.add(filePath);
		try {
			this.loadChunk(fs.readFileSync(filePath), `@${filePath}`);
			pcallChecked(L, 0, 1);
			// Lua 的 require 约定：模块没有返回值时返回 true
			if (lua.lua_type(L, -1) === lua.LUA_TNIL) {
				lua.lua_pop(L, 1);
				lua.lua_pushboolean(L, true);
			}
			const ref = lauxlib.luaL_ref(L, lua.LUA_REGISTRYINDEX);
			this.moduleRefs.set(name, ref);
			lua.lua_rawgeti(L, lua.LUA_REGISTRYINDEX, ref);
			return 1;
		} catch (error) {
			this.logger.warn(`publish: [${this.pluginName}] require("${name}") failed: ${error.message}`);
			return raise(L, `error loading module '${name}': ${error.message}`);
		} finally {
			this.loadingModules.delete(filePath);
		}
	}

	loadMain() {
		if (!isFile(this.mainPath)) throw new Error(`Lua plugin entry not found: ${this.mainPath}`);
		this.loadChunk(fs.readFileSync(this.mainPath), `@${this.mainPath}`);
		pcallChecked(this.L, 0, 0);
	}

	buildPackages() {
		const root = this.doc.getRoot();
		const packages = (typeof root.listPackages === "function" ? root.listPackages() : []).map((pkg) => ({
			name: pkg.getName(),
			id: typeof pkg.getId === "function" ? pkg.getId() : "",
			items: buildItems(pkg)
		}));
		// FairyGUI 编辑器传进来的是 0 基下标集合，Lua 侧用 packages.Length 取长度
		packages.Length = packages.length;
		return packages;
	}

	callGlobal(hook, args) {
		const L = this.L;
		lua.lua_getglobal(L, to_luastring(hook));
		if (lua.lua_type(L, -1) !== lua.LUA_TFUNCTION) {
			lua.lua_pop(L, 1);
			return false;
		}
		for (const arg of args) interop.push(L, arg);
		pcallChecked(L, args.length, 0);
		return true;
	}

	createHooks() {
		return {
			onPublishStart: (doc) => {
				const before = this.countExported();
				if (!this.callGlobal("onPublishStart", [this.buildPackages()])) return;
				for (const [name, count] of this.countExported()) {
					const previous = before.get(name);
					if (previous !== undefined && previous !== count) {
						this.logger.info(`publish: [${this.pluginName}] ${name}: exported ${previous} -> ${count}`);
					}
				}
				this.logger.info(`publish: [${this.pluginName}] onPublishStart handled by Lua`);
			},
			onPublishEnd: () => {
				this.callGlobal("onPublishEnd", [this.buildPackages()]);
			},
			onDestroy: () => {
				this.callGlobal("onDestroy", []);
			}
		};
	}

	countExported() {
		const counts = new Map();
		const root = this.doc.getRoot();
		const packages = typeof root.listPackages === "function" ? root.listPackages() : [];
		for (const pkg of packages) {
			const resources = typeof pkg.listResources === "function" ? pkg.listResources() : [];
			counts.set(pkg.getName(), resources.filter((resource) => resource.getExported?.()).length);
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
