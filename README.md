# 修行日历订阅包

这个包会自动生成 4 个 `.ics` 订阅源：

- `six-zhai.ics`：六斋日，事件名写成 `斋戒-十四`、`斋戒-十五` 这类格式。
- `extra-ten-zhai.ics`：十斋日里额外加上的日子，事件名写成 `初一`、`十八`、`廿四`、`廿八`。
- `spiritual.ics`：灵性事件，包含 `新月`、`满月`、`星门 1.1` 到 `星门 12.12`。
- `combined.ics`：合并版，方便你只订阅一个链接时使用。

## 重要说明

Apple Calendar 的颜色是“按日历”而不是“按单个事件”来显示，所以如果你想要绿色 / 橘色 / 蓝色三种颜色同时存在，最稳妥的方式是 **订阅 3 个不同的日历源**，再分别把它们设成绿色、橘色、蓝色。

## 一次性部署到 GitHub Pages

1. 新建一个 GitHub 仓库。
2. 把这个压缩包里的全部内容上传到仓库根目录。
3. 在仓库的 **Settings → Pages** 中，把站点来源设为 **Deploy from a branch**。
4. Branch 选 `main`，Folder 选 `/docs`。
5. 保存后，GitHub 会给你一个 Pages 地址，例如：
   - `https://你的用户名.github.io/你的仓库名/six-zhai.ics`
   - `https://你的用户名.github.io/你的仓库名/extra-ten-zhai.ics`
   - `https://你的用户名.github.io/你的仓库名/spiritual.ics`
   - `https://你的用户名.github.io/你的仓库名/combined.ics`

## 自动更新

仓库里已经带了 GitHub Actions 工作流：

- 每月自动运行一次。
- 自动重建“今年起连续 4 年”的订阅文件。
- 自动提交回仓库，所以 Pages 链接保持不变。

如果你想手动刷新，也可以在 GitHub 的 **Actions** 页面手动运行工作流。

## 在 Apple Calendar 中订阅

### iPhone / iPad

- 设置 → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar
- 粘贴上面的 `.ics` URL
- 分别给三个日历设成绿色、橘色、蓝色

### Mac

- Calendar → File → New Calendar Subscription
- 粘贴 `.ics` URL
- 订阅后修改日历颜色

## 改时区

默认时区是 `America/New_York`，比较适合你在费城使用。若你之后想改成中国时区，可以把工作流里的参数改成：

```bash
python generate_calendars.py --timezone Asia/Shanghai
```
