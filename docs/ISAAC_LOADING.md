# 在 Isaac Sim 中加载物体

本仓库包含物体模型、碰撞、质量、惯性、材质及旋转关节。
使用 **Isaac Sim 5.1.0 / Python 3.11**，不需要 Isaac Lab。

## 1. 下载与环境

```bash
git clone https://github.com/yuzhen-song/isaac-model.git
cd isaac-model
```

已有 Isaac Sim 5.1 环境时，直接激活该环境。从零安装可执行：

```bash
conda create -n arctic-isaac51 python=3.11 -y
conda activate arctic-isaac51
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt --extra-index-url https://pypi.nvidia.com
```

需要 NVIDIA GPU 和兼容驱动；首次启动按提示接受 NVIDIA 许可。
Ubuntu 容器缺少图形库时，管理员可安装：

```bash
apt-get update
apt-get install -y libxt6 libglu1-mesa libvulkan1
```

## 2. 最快加载方法

在仓库根目录运行：

```bash
python examples/load_object.py --object microwave --headless --allow-root
python examples/load_object.py --object espresso --headless --allow-root
```

脚本建立桌面和物理场景，加载指定物体并运行 3 秒。
成功结束打印 `LOAD_SMOKE_CHECK_COMPLETED`。有桌面图形界面时去掉 `--headless`。
如果 AutoDL 出现之前的 NVIDIA GLX/Vulkan 加载问题，先执行：

```bash
source scripts/enable_egl.sh
```

## 3. 在 Isaac Sim 界面打开

| 物体 | 完整演示场景：直接打开并按 Play | 独立物体入口：加入已有场景 |
| --- | --- | --- |
| 咖啡机 | `objects/espresso/espresso_test.usda` | `objects/espresso/espresso_asset.usda` |
| 微波炉 | `objects/microwave/microwave_test.usda` | `objects/microwave/microwave_asset.usda` |

完整演示场景包含桌面、灯光和相机。独立物体入口停用这些环境内容，保留物体本身
和材质；加载到已有场景时，由已有场景提供桌面及 PhysicsScene。

请保留完整仓库，或至少复制完整的物体文件夹。`*_asset.usda` 通过相对路径引用
同目录的 `*_test.usda`，不能只复制入口文件。

## 4. 用代码加入已有场景

下面代码放在 `SimulationApp` 已启动、现有 Stage 已建立、物理尚未开始的位置。
把 `repo` 改为本机克隆路径：

```python
from pathlib import Path
import sys
import omni.usd

repo = Path("/absolute/path/to/isaac-model")
sys.path.insert(0, str(repo))
from scripts.spawn_object import spawn_object

stage = omni.usd.get_context().get_stage()
paths = spawn_object(
    stage,
    object_name="microwave",  # 咖啡机用 "espresso"，也支持 "espressomachine"
    prim_path="/World/Objects/microwave",
    position=(0.0, 0.0, 0.0),
    orientation_wxyz=(1.0, 0.0, 0.0, 0.0),
)
print(paths)
```

也可以直接使用 Isaac Sim 5.1 的 USD 引用接口：

```python
from isaacsim.core.utils.stage import add_reference_to_stage

add_reference_to_stage(
    usd_path=str(repo / "objects/microwave/microwave_asset.usda"),
    prim_path="/World/Objects/microwave",
)
```

模型已使用 **米、千克、Z 轴向上**，加载比例为 **1**，无需再做毫米转米。
`position` 是模型装配原点的位置，四元数顺序为 **w,x,y,z**。
在不同 prim 路径可以加载多个实例。`spawn_object` 会返回当前实例的刚体和关节路径。

## 5. 已配置的参数

| 物体 | 刚体质量 | 旋转关节 |
| --- | --- | --- |
| 咖啡机 | Body 0.55069 kg；Handle 0.00653 kg | `Espresso/handle_hinge` |
| 微波炉 | Body 约 0.48839275 kg；Door 约 0.03516145 kg | `Microwave/door_hinge` |

白色 PLA 外观、质量、惯性、凸分解碰撞和被动关节阻力已写入 USD。
两种物体均可移动，旋转关节均**不设角度限位**，无需额外添加这些设置。
微波炉质量按 PLA、15% 填充及约定外壳参数估算，详细假设见其 README。

各文件的用途、质量来源、原验证与录制命令见物体目录中的 README。
新增独立入口的材质引用、多实例路径、关节与单位已通过 OpenUSD 静态检查，见
[`validation/integration_static.json`](../validation/integration_static.json)。
新增加载示例尚未在本机 GPU 上运行；服务器之前成功运行的是原完整验证场景。
