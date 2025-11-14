#!/bin/bash
# GitHub仓库设置脚本

echo "=== Teable CLI GitHub仓库设置 ==="
echo ""
echo "请选择创建方式："
echo "1. 使用GitHub CLI (gh) - 需要先安装: brew install gh"
echo "2. 手动创建（推荐）- 我会提供步骤"
echo ""
read -p "请选择 (1/2): " choice

if [ "$choice" = "1" ]; then
    if ! command -v gh &> /dev/null; then
        echo "❌ GitHub CLI未安装，请先运行: brew install gh"
        echo "然后运行: gh auth login"
        exit 1
    fi
    
    echo "正在创建GitHub仓库..."
    gh repo create teable-cli --public --source=. --remote=origin --push
    echo "✅ 仓库创建完成并已推送代码"
    
elif [ "$choice" = "2" ]; then
    echo ""
    echo "=== 手动创建GitHub仓库步骤 ==="
    echo ""
    echo "1. 访问 https://github.com/new 创建新仓库"
    echo "2. 仓库名称建议: teable-cli"
    echo "3. 选择 Public 或 Private"
    echo "4. 不要初始化 README、.gitignore 或 license（我们已经有了）"
    echo "5. 点击 'Create repository'"
    echo ""
    read -p "创建完成后，请输入你的GitHub用户名: " username
    read -p "请输入仓库名称（默认: teable-cli）: " repo_name
    repo_name=${repo_name:-teable-cli}
    
    echo ""
    echo "正在添加远程仓库..."
    git remote add origin "https://github.com/${username}/${repo_name}.git" 2>/dev/null || \
    git remote set-url origin "https://github.com/${username}/${repo_name}.git"
    
    echo "正在推送代码..."
    git branch -M main
    git push -u origin main
    
    echo ""
    echo "✅ 完成！仓库地址: https://github.com/${username}/${repo_name}"
else
    echo "❌ 无效选择"
    exit 1
fi

