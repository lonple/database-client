# =============================================================================
# dbc-front：多阶段构建 —— 打包静态资源并打进 nginx 镜像
# =============================================================================
# 阶段 build：Node 内执行 npm run build，产出 dist/
# 阶段最终：nginx 托管 dist，反代 /dbc-* → dbc-gateway:8003
# 由 compose build dbc-front 触发，无需事先在宿主机 npm（build-docker-apps 仍可本地 npm 便于检查）
# 基础镜像需与本机已 pull 的标签一致（断网环境）：node:26.8.2-slim
# =============================================================================

# ----- 阶段 1：前端打包 -----
FROM node:26.8.2-slim AS build
WORKDIR /src
# 先只拷依赖清单，利用层缓存
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
# 再拷源码并构建
COPY . .
RUN npm run build

# ----- 阶段 2：运行镜像 -----
FROM nginx:stable-alpine
# 从上一阶段拷贝构建产物到 nginx 默认站点目录
COPY --from=build /src/dist /usr/share/nginx/html
# 默认反代配置（可被 compose 挂载的工作区 conf 覆盖）
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
