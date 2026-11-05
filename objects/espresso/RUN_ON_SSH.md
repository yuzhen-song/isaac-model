# 新版咖啡机：上传、仿真、录制、成功后发布

本次源 STEP 的 SHA-256：
`338b6787ffbdb3f9d80bba38385c2abcda6ae35f4dda30a289948efa58a8ad5c`。
网格已按最新 STEP 重新生成，没有使用旧的 stick.STL。

## Windows PowerShell：上传

```powershell
scp -P 17844 "C:\Users\L\OneDrive\文档\ChatGPT\SignHOI\Espresso_Isaac_Handoff.zip" root@connect.bjb1.seetacloud.com:/root/Espresso_Isaac_Handoff_20261105.zip
```

## SSH Linux 终端：运行

```bash
conda activate /root/autodl-tmp/isaac51
python -m zipfile -e /root/Espresso_Isaac_Handoff_20261105.zip /root/autodl-tmp/espresso_revision_20261105
cd /root/autodl-tmp/espresso_revision_20261105/Espresso_Isaac_Handoff
python -u run_checks_and_record.py
```

脚本依次执行 10 秒静置、固定机身关节检查、11 秒动态开关手柄录制。
沿用现有 Isaac 环境及原服务器的 EGL 配置文件。全部通过会显示 `ALL_CHECKS_PASSED`，
输出视频 `espresso_open_close_updated.mp4` 以及 JSON、CSV、日志和成功记录。
任一步失败就停止；此步骤不会修改 GitHub。

## Windows PowerShell：下载视频

```powershell
scp -P 17844 root@connect.bjb1.seetacloud.com:/root/autodl-tmp/espresso_revision_20261105/Espresso_Isaac_Handoff/espresso_open_close_updated.mp4 "D:\nkd\2026FALL_UC_Berkeley\HOI\new_objects\espressomachine\espresso_open_close_revision_20261105.mp4"
```

## 成功后，在 SSH 中发布

```bash
cd /root/autodl-tmp/espresso_revision_20261105/Espresso_Isaac_Handoff
python publish_revision.py
```

需要 `gh` 已登录且有仓库写权限。上传脚本会验证本次全部检查结果，并核对测试前后
模型/脚本与输出哈希；缺报告、失败或文件变化都会拒绝发布。
成功后更新 `yuzhen-song/isaac-model` 中的咖啡机模型、视频、验证记录及相关说明。
