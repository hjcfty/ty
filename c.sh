#!/data/data/com.termux/files/usr/bin/bash

# 0. 安全锁：防止接口备份被清空导致仓库被清空
if [ -z "$(ls -A /storage/emulated/0/接口备份/)" ]; then
    echo "⚠️ 接口备份文件夹为空，为保护仓库已停止上传。"
    exit 1
fi

# 1. 把接口备份里的所有东西（含文件夹）覆盖复制到仓库
cp -r /storage/emulated/0/接口备份/* ~/cfty/

# 2. 进入仓库文件夹
cd ~/cfty

# 3. 检查有没有文件变化
if git diff --quiet && git diff --cached --quiet; then
    echo "📭 没有新变化，不用上传。"
else
    echo "📦 检测到变化，正在上传..."
    
    # 自动追踪所有改动（包含新增、修改、删除）
    git add -A
    
    # 列出本次改动的文件清单
    echo "---------- 本次同步的文件 ----------"
    git status -s
    echo "-----------------------------------"
    
    # 同步远程最新改动（防止网页端改过导致推送失败）
    git pull --rebase
    
    # 提交并推送
    git commit -m "自动同步 $(date +%Y-%m-%d)"
    git push
    echo "✅ 上传成功！"
fi
