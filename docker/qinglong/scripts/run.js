"use strict";

// 每次启动都读取宿主机文件；不将 Token 复制到面板、Compose 或命令行。
const fs = require("fs");
const path = require("path");
const tokenFile = "/zeekr/configs/极氪本人token.txt";
const entries = new Set([
  "zeekr_0001_all.js",
  "zeekr_0010_claim.js",
  "zeekr_0810_all.js",
  "zeekr_0820_claim.js",
  "zeekr_2130_all.js",
  "zeekr_2140_claim.js",
]);

function main() {
  const arg = process.argv[2];
  if (process.argv.length !== 3 || (arg !== "--check" && !entries.has(arg))) {
    throw new Error("请指定六个极氪入口文件之一，或使用 --check 仅检查配置。");
  }
  const raw = fs.readFileSync(tokenFile, "utf8");
  const tokens = raw.match(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g) || [];
  if (tokens.length !== 1) {
    throw new Error("Token 文件必须包含且仅包含一个完整 JWT，可带 Bearer 前缀。");
  }
  let claims;
  try {
    claims = JSON.parse(Buffer.from(tokens[0].split(".")[1], "base64url").toString("utf8"));
  } catch (_) {
    throw new Error("Token 的 JWT 内容无法解析，请更新原文件。");
  }
  if (!Number.isFinite(claims.exp) || claims.exp * 1000 <= Date.now()) {
    throw new Error("Token 缺少有效到期时间，或已超过声明到期时间，请更新原文件。");
  }
  if (arg === "--check") {
    console.log("配置检查通过：从映射文件读取到 1 个 Token；JWT 声明到期时间 " +
      new Date(claims.exp * 1000).toISOString() + "。服务器是否接受以实际任务结果为准。");
    return;
  }
  // 原文件是本部署唯一的账号来源，避免面板旧变量重复执行或改变补领模式。
  for (const key of Object.keys(process.env)) {
    if (/^ZEEKR_TOKEN(?:_\d+)?$/i.test(key) || /^(?:ZEEKR_)?VAL(?:_\d+)?$/i.test(key) ||
        key === "ZEEKR_SINGLE_VARIABLE") {
      delete process.env[key];
    }
  }
  process.env.ZEEKR_TOKEN = "Bearer " + tokens[0];
  console.log("[本机部署] 已读取映射的 Token 文件，执行 " + arg);
  require(path.join("/zeekr/entries", arg));
}

try {
  main();
} catch (error) {
  // 不输出文件内容、原始异常或进程环境，避免泄露凭据。
  const known = error.code === "ENOENT" ? "找不到映射的 Token 或入口文件。" :
    error.code === "EACCES" ? "无法读取映射的 Token 或入口文件。" :
    error.message;
  console.error("[本机部署] " + known);
  process.exitCode = 1;
}
