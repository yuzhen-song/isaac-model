# Microwave — white PLA, 15% infill estimate

源文件为用户提供的 `microwave.STEP` 装配及 4 个 STL，原 CAD 未修改。
已生成可以在 Isaac Sim 5.1 中打开的场景：**`microwave_test.usda`**。
单位为米、千克，Z 轴向上；门的零位保持 STEP 导出的装配姿态。

## 材料与重量

白色 PLA 密度假定为 **1.24 g/cm³**，内部稀疏填充率为 **15%**。
按以下缺省打印参数进行几何逐层估算：

- 0.4 mm 喷嘴，2 道壁，壁厚近似 0.8 mm。
- 层高 0.2 mm，顶层和底层各 3 层，即各约 0.6 mm。
- 每个原始 STL 的局部 Z 轴作为打印方向。
- 保留实心外壁与顶底层，仅在内部区域采用 15% 填充。

| 部件 | 估计重量 |
| --- | ---: |
| 机身 bottom1 | 486.93 g |
| 门 door | 35.16 g |
| 插销 1 | 1.23 g |
| 盖子 2 | 0.24 g |
| 总计 | 523.55 g |

这是**几何近似估重，不是 Bambu Studio 实际切片耗材或称重结果**。
未计入支撑、Brim、冲刷废料；未模拟实际路径搭接、可变线宽和桥接规则。
打印方向或外壳参数变化后，重量也会变化。
`mass_estimate.json` 保存了全部假设、各部件体积、外壳/内部区域分解和计算结果。

质量已实际写入 USD：插销和盖子与机身组成一个刚体，Body 总质量约
**0.48839275 kg**，Door 约 **0.03516145 kg**。没有重复计算插销和盖子的重量。
重心和惯性按各部件等效均匀密度估算；视觉与碰撞不显式建立内部填充晶格。

## 仿真设置

- 主场景：`microwave_test.usda`，机身可移动，由台面支撑。
- 固定机身测试覆盖：`microwave_fixed_base.usda`。
- `/World/Microwave/Body` 是机身、插销与盖子的组合刚体。
- `/World/Microwave/Door` 是门刚体。
- `/World/Microwave/door_hinge` 为旋转关节，**上下限为负/正无穷，无角度限位**。
- 开门测试默认负向旋转；0 → −90° → 0 是示例目标，不是限位。
- 关节采用暂定的 **0.02 N·m** 上限制动近似，沿用之前咖啡机配置，
  未实测微波炉阻力。angular Drive：stiffness=0、targetVelocity=0、
  damping=1 N·m·s/degree、maxForce=0.02 N·m。这不是精确库仑/静摩擦模型。
- 外部接触静摩擦系数 0.5、动摩擦系数 0.4、恢复系数 0，均为未校准占位值。
- Body 与 Door 之间关闭接触以采用理想铰链约束；不模拟内部轴孔接触或本体互碰产生的挡块。
  与机器人、桌面等外部对象的接触仍启用。
- 动态碰撞网格采用凸分解，实际生成的凸包需在 Isaac 中检查。

## 环境与运行

使用 Isaac Sim **5.1.0 / Python 3.11**；不需要 Isaac Lab。
已有环境可直接运行以下命令；新环境可安装：

```bash
python -m pip install 'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com
python -m pip install imageio imageio-ffmpeg
```

在本目录检查动态场景，保留质量和被动制动器，不施加运动指令：

```bash
python run_passive_scene.py --headless --allow-root --seconds 10
```

检查固定机身的独立关节跟踪：

```bash
python run_isaac_check.py --headless --allow-root
```

此测试只在内存中用电机覆盖被动制动器，不修改场景文件，不验证实际阻力或机身稳定性。

录制开门和关门，保留动态机身、15% 填充估算质量和原有制动器：

```bash
python -u record_microwave_motion.py --headless --allow-root
```

输出 `microwave_open_close.mp4`、同名 JSON/CSV，1280×720、30 fps、11 秒。
录制通过外加测试力矩转门，并向机身施加反作用力矩；不是机械手操作成功示范。
请检查 JSON 中的 `motion_checks_passed`，不能仅凭生成视频就判定物理测试通过。

之前 AutoDL 咖啡机环境已经配置好 EGL 时，可沿用：

```bash
mkdir -p /tmp/isaac-runtime
chmod 700 /tmp/isaac-runtime
XDG_RUNTIME_DIR=/tmp/isaac-runtime \
VK_ICD_FILENAMES=/root/autodl-tmp/nvidia_egl_icd.json \
python -u record_microwave_motion.py --headless --allow-root
```

上述 EGL 路径是原服务器专用配置；正常图形环境不一定需要该变量。
NVIDIA 许可和驱动要求参考官方 Isaac Sim 5.1 安装文档。

## 文件与验证状态

- `source_cad/`：原始 SW 装配、零件、STEP。
- `meshes_assembly_mm/`：恢复原装配位置后的 STL，单位 mm。
- `meshes_sim_m/`：仿真用 Z-up STL，单位 m。
- `joint_parameters.json`：质量、关节、阻力、碰撞和估算假设。
- `docs/geometry_validation.json`：STL 与 STEP 表面抽样对齐验证。
- `docs/usd_static_validation.json`：USD 质量、惯性和关节静态验证。

已完成本地静态检查。用户已报告在 Isaac Sim 5.1 完成静置、关节测试与录制。
[开关门视频](media/microwave_open_close.mp4)已归档并核对视频元数据：330 帧、30 fps、11 秒、1280×720。
微波炉数值运行报告尚未归档，因此没有独立复核其跟踪判据；验证来源见 [运行摘要](validation/runtime_summary.json)。
`docs/usd_static_validation.json` 保留的是打包时静态检查，其运行标志早于后续服务器测试。
外部接触、阻力标定和真机操作需单独验证。
