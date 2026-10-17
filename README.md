# 在 Linux 上运行 Intel Xcode：实验检查点

本分支保存截至 **2026-10-17** 的 Linux x86_64 / Darling 实验脚本、测试、配置、源码补丁和进展说明。目标是运行原版 `xcodebuild`、保留 Xcode 工程及 CI 命令，所有执行发生在 Linux，不依赖 Mac。

**完整 Xcode 构建与签名尚未完成。** 原版 clang、clang++、ld、dsymutil 已在 Darling 中实际编译、链接并生成调试符号；原版 `xcodebuild` 已启动原版 SwiftBuild 服务，计算依赖图、创建构建描述，并执行目录、头文件映射和响应文件任务。目前工程构建在 `clang-stat-cache` 缺少 `FSEventsGetCurrentEventId` 时以真实状态码 65 失败，尚未通过 `xcodebuild` 完成源文件编译及链接。Unity/CocoaPods 全流程、归档、签名、导出均未完成。

工程进展使用单独的宽松 CoreServices Sandbox 诊断配置；严格 Sandbox 策略附加与完整执行限制仍不完备。历史探测、兼容层及实验脚本不代表它们都已成为默认运行环境。

## 保存在哪里

- [Darling 源码分支](https://github.com/kxn/darling/tree/linuxcode/xcode-x86_64)：主仓库修改，以及指向个人 fork 确切提交的已修改子模块。
- [darlingserver 源码分支](https://github.com/kxn/darlingserver/tree/linuxcode/xcode-x86_64)：Mach、S2C 线程生命周期、FSEvents、Sandbox 等服务端修改。
- [源码版本清单](checkpoint/source-manifest.json)：每个 fork 的地址、上游基础提交、保存提交、补丁校验和及修改文件校验和。
- [详细进展与历史复现命令](docs/PROGRESS.md)：完整本地实验记录。按记录区分当前候选、历史阶段和未完成事项。
- `scripts/`、`bin/`、`config/`、`fixtures/`、`build-support/`：构建、启动、测试、探测及示例工程。
- `checkpoint/evidence/`：选取的本地测试记录与进展摘要，**不是完整运行产物归档**。完整的本地报告、历史输入和二进制仍在原机器；摘要中的路径和 SHA 不能替代缺失的产物。

子模块修复包括 libxpc、xnu/libsystem_kernel、IOKitUser、iokitd、libtrace、libnotify、corecrypto、dyld、objc4、libc++ 等；它们不是只放在主仓库中的空指针引用，每个修改仓库都有独立 fork 和源码提交。

## 恢复源码实验状态

现有阶段脚本会验证 `HEAD` 等于当时的上游基础提交。直接检出源码分支适合审查，但不满足这些旧脚本的 revision 校验。下面的恢复工具检出上游基础版本，再应用已保存、已校验的完整补丁，重建原实验的“基础 HEAD + 工作区源码修改”状态：

```bash
git clone --single-branch --branch linuxcode/workspace-2026-10-17 https://github.com/kxn/darling.git linuxcode
cd linuxcode
python3 checkpoint/restore-sources.py --clone
python3 checkpoint/restore-sources.py --verify
```

下载 Darling 及其递归子模块需要网络、时间和磁盘。工具不重置现有仓库；基础版本不同或发现冲突会报错，避免覆盖已有工作。重复执行会识别已恢复的文件。只想审查改动时，直接查看源码分支和清单中的提交即可。

**恢复源码不等于一键恢复完整运行环境。** `scripts/bootstrap.sh` 保存原先的 Linux 用户态初始化流程；后续构建还依赖 LLVM 19、主机工具、相应的本地 SDK、Xcode、恢复镜像和阶段运行根。部分配置包含这台机器原始输入的 SHA，阶段记录也可能引用仅本地保留的历史产物。因此本检查点保存了可继续开发的代码、来源与证据，未宣称已在全新机器上完成端到端复现。请结合 `docs/PROGRESS.md` 的阶段顺序和各脚本前置检查操作。

## 当前主要源码进展

- libxpc：连接激活失败的真实错误交付，以及同步、异步、取消和共享内存生命周期修复。
- libsystem_kernel：线程 materialization 策略、挂载标志、文件元数据/FSEvents/Sandbox 桥接；默认致命信号和 abort 仅针对当前进程，避免连带终止父脚本。
- darlingserver：远程内存映射、S2C 活线程选择、Linux FSEvents 设备后端和 Sandbox 查询/解析。
- IOKit/notifyd：真实 Mach 通知、匹配/电源通知生命周期与 Linux 挂载变化观察。
- MobileAsset：真实 XPC 查询编码、结果解码、错误及异步回调；不含资产下载/安装服务。
- 其他：源代码密码后端、Security RPC、日志、目录服务、运行时 ABI 与框架兼容补充。具体限制见进展记录。

正常候选与宽松诊断候选分别保留；原版 Xcode 未被改写。部分阶段需要在本地重建或选取 Apple 原版运行库，这不等于实现了对应服务的全部语义。

## 文件边界

仓库不包含 Xcode/XIP、Apple SDK、恢复镜像、提取或重建的 Apple 二进制、运行根、core dump、证书私钥、签名凭据或下载缓存。使用者必须自行提供所需输入。源码保留各上游原有版权及许可；本分支不重新许可第三方源码。`checkpoint/sources/` 是相应上游基础提交上的源码差异。
