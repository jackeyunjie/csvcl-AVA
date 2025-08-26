# Git私有仓库上传操作指南

## 🔒 第一步：在Gitee创建私有仓库

1. **登录Gitee账户**: https://gitee.com/yiyidedao
2. **点击右上角 "+" → "新建仓库"**
3. **填写仓库信息**:
   ```
   仓库名称: mt4-data-processor
   仓库介绍: MT4数据自动处理系统（私人项目）
   仓库类型: 私有 ✓ （重要！）
   语言: Python
   添加README: 否（我们已经有了）
   添加.gitignore: 否（我们已经有了）
   ```
4. **点击"创建"**

## 💻 第二步：本地Git操作

打开命令行（在项目文件夹 d:\qoder\csvcl 中），依次执行：

### 1. 初始化仓库
```bash
git init
```

### 2. 添加所有文件
```bash
git add .
```

### 3. 检查要提交的文件（可选）
```bash
git status
```
**确认**: 不应该看到 email_config.ini 或任何 .xlsx/.jpg 文件

### 4. 提交到本地仓库
```bash
git commit -m "初始版本：完整的MT4数据自动处理系统

功能特性：
- ✅ MT4数据自动处理
- ✅ E2:G40区域颜色标记
- ✅ A1:M40高清截图生成
- ✅ 7:00-22:00自动邮件发送
- ✅ 数据变化智能分析
- ✅ 多收件人支持
- ✅ 私有仓库安全保护"
```

### 5. 连接远程仓库
```bash
git remote add origin https://gitee.com/yiyidedao/mt4-data-processor.git
```

### 6. 推送到远程仓库
```bash
git push -u origin master
```

## ✅ 第三步：验证上传结果

1. **访问仓库**: https://gitee.com/yiyidedao/mt4-data-processor
2. **检查隐私设置**: 确认显示"私有"标识
3. **检查文件列表**: 确认包含以下文件
   - ✅ README_NEW.md
   - ✅ .gitignore
   - ✅ email_config.ini.template
   - ✅ requirements.txt
   - ✅ 所有.py文件
   - ❌ email_config.ini（不应该出现）
   - ❌ 任何.xlsx/.jpg文件（不应该出现）

## 🏷️ 第四步：创建版本标签（可选）

```bash
git tag -a v1.0.0 -m "完整功能版本"
git push origin v1.0.0
```

## 🔄 日常使用命令

### 提交新的更改
```bash
git add .
git commit -m "更新描述"
git push
```

### 查看状态
```bash
git status        # 查看文件状态
git log --oneline # 查看提交历史
```

## 🛡️ 安全检查清单

- [ ] 仓库设置为私有
- [ ] email_config.ini 未被提交
- [ ] 所有临时文件已被.gitignore排除
- [ ] 配置模板文件已创建
- [ ] README文件信息完整

## ❗ 常见问题

**Q: 推送时要求用户名和密码？**
A: 输入您的Gitee用户名和密码

**Q: 推送失败？**
A: 检查远程仓库地址是否正确，确保仓库已创建

**Q: 意外提交了敏感文件？**
A: 可以使用 `git rm --cached filename` 移除，然后重新提交

---

🎉 **完成后，您就有了一个安全的私有代码仓库！**