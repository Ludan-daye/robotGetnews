# 使用nginx作为前端服务器
FROM nginx:alpine

# 复制前端文件到nginx默认目录
COPY . /usr/share/nginx/html/

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]