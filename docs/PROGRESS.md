# Linux 上的 Intel Xcode 实验环境

已建立独立的 x86_64 Darling 用户态环境，解压并导入用户提供的 `Xcode_26.6_Universal.xip`。原版 Xcode 26.6（17F113）的 clang、clang++、ld、dsymutil 已在 Linux 上实际编译、链接 iOS 程序，并生成调试符号；编译出的 macOS x86_64 程序也已在 Darling 中运行。

**目前还不能作为完整 Xcode CI 环境使用。** 原版 `xcodebuild` 已能启动原版 SwiftBuild 服务、计算依赖图、创建构建描述，并实际执行目录、头文件映射和响应文件生成任务。当前工程返回真实退出码 65：`clang-stat-cache` 加载不到 `FSEventsGetCurrentEventId`，尚未完成源文件编译和链接。正常候选的 `-version`、`-showsdks` 和严格 UTI 预检通过。Unity/CocoaPods、iOS/macOS 归档、签名、导出及默认 CI 入口集成仍未完成。主检查点为 `artifacts/native-crypto-progress.json`。

## FSEvents 递归监测与历史缺失通知（2026-10-19）

继续核对原版 Intel `clang-stat-cache` 后，发现缺失全局事件 ID 之后还有第二个实际问题：原 Darling FSEvents 忽略 `sinceWhen`，不会发送 `HistoryDone`。对用户提供的原版工具反汇编确认，它创建无附加 flags 的流、绑定主 dispatch queue 并进入 `CFRunLoopRun`；回调检查 `0x10` 历史结束标志，其他事件使缓存失效，只有收到结束标志才停止 run loop。缺失通知会导致缓存复用等待，而非仅仅缺少一个导出符号。

已直接修改 Darling 的两个 FSEvents 源文件及内部头：传递 `sinceWhen`，对无法回放的历史明确发送每个根的 `MustScanSubDirs | UserDropped`，随后发送一次独立的 `HistoryDone`，避免把未观察到的历史当成“没有变化”。实现目录递归监测、创建子树后的实际监测及覆盖缺口通知、目录改名后的路径更新和移出监测范围后的解除监测；不追踪子目录符号链接形成的循环。目录遍历使用迭代队列，限制 65,536 个 watch；初始覆盖失败返回失败，不静默报告完整覆盖。历史缺失要求重新扫描的语义见 [Apple FSEvents 指南](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/FSEvents_ProgGuide/UsingtheFSEventsFramework/UsingtheFSEventsFramework.html)。

完整重编译两源文件组件，保留 29 个原有导出。原生验证覆盖有限历史、单次结束边界、重启、既有及新增深层目录、真实目录移动、外部链接排除，并按原版工具使用的 C 路径数组 ABI 验证主队列/CF run loop 能收到历史结束后返回。新检查 84 项、既有 flush 回归 88 项、小栈测试在 64 KiB 线程上收到两个真实事件。原版 `-version`、`-showsdks` 与严格 UTI 预检通过；首次 SDK 列表命令本身返回 0，但随后清理阶段出现 semaphore 错误和外层超时，已保留失败记录，独立串行重试完整退出 0。尚未证明该次清理故障的根因，也未把它记为成功退出。

工程复测还暴露了服务端的二次故障：`task_map_corpse_info_64` 的未实现路径执行 `__builtin_unreachable()`，server 消失后多个客户端报告 RPC 断连；首轮工程的外层退出 -9，脚本记录 Xcode 132，不能算作原先的 65 结果。该失败及 server 日志已保留。随后在调试器下重跑时未重现首次异常，工程回到原先的缺失全局 ID 报错；不能据此认定此前故障的完整触发原因。直接修复 server 的 32/64 位 corpse-info 映射参数检查：普通活任务、无效任务、forked-corpse 目的任务和缺失 corpse 数据返回 `KERN_INVALID_ARGUMENT`；有效 corpse 的真实数据映射仍不支持，返回 `KERN_NOT_SUPPORTED`，不虚构成功。8 个并发线程的原生测试执行 512 次真实 Mach RPC 错误返回和 256 次实际内存分配/释放，共 1,808 项检查通过，服务持续存活。新 server 候选的 SDK 查询也曾在命令返回 0 后，于 40 秒外层上限下清理超时（124）；将外层上限扩展至 120 秒的后续复测完整退出 0。该差异如实保留，未把延长等待当成清理根因修复。最终原版版本查询、SDK 列表、严格 UTI 和工程复测均完成退出，工程仍返回缺失全局 ID 的 65。

**没有实现 `FSEventsGetCurrentEventId`、系统共享事件 ID 或持久历史日志。** 当前事件编号仍是每流计数，不能当作全局 ID。以上是全局事件源接入之前必须补齐的监测和失效语义；未关闭缓存、改写原版工具或修改工程构建参数，默认入口未推广。原版工程当前仍在 `clang-stat-cache` 的全局 ID 依赖处失败，完整编译、链接和签名尚未完成。

```bash
python3 scripts/build-fsevents-source.py --output-dir runtime/fsevents-history-source --report artifacts/fsevents-history-source-build.json
python3 scripts/test-fsevents-history.py --baseline
python3 scripts/test-fsevents-history.py
python3 scripts/analyze-stat-cache-fsevents.py
python3 scripts/build-corpse-map-server.py
python3 scripts/stage-corpse-map-runtime.py
python3 scripts/test-corpse-map-errors.py
python3 scripts/probe-xcode-service-runtime.py version --corpse-map --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --corpse-map --cfprefsd-daemon --timeout-seconds 120
python3 scripts/probe-xcode-service-runtime.py build --corpse-map --core-volume-diagnostic --cfprefsd-daemon --filecoordination --timeout-seconds 180
```

新框架在 `runtime/fsevents-history-source/frameworks/`，新增 server 选入独立的 `runtime/corpse-map-normal/` 和 `runtime/corpse-map-diagnostic/`；工程尝试仍使用单独的宽松 CoreServices 策略。报告：`artifacts/fsevents-history-progress.json`；源码补丁：`artifacts/darling-fsevents-recursive-history-source.patch`、`artifacts/darlingserver-corpse-map-errors-source.patch`。先前源码、精确基线测试输入、工程及 SDK 清理失败记录均按 SHA 保存。下一步是共享事件源与真实全局 ID，并验证原版 stat-cache 的首次生成、无变化复用和真实变更失效。

## ICU 数据、致命信号与原版 SwiftBuild 任务（前一补充）

进一步跟踪纠正了“原版 Xcode 一直等待”的判断：Linux 现场显示主线程在地址 0x8 发生 SIGSEGV，Darling 随后执行 `kill(0, SIGSEGV)`，连同父脚本和同组进程一起结束，外层只留下返回码 1。正确换算 x86_64 fat slice 与 Mach-O segment 的故障栈落在 CoreFoundation 的类型检查，调用方是 Security 的数字参数转换及 SwiftPM 的 RSA 公钥／证书导入。

实际加载的原版 ICU 是 78.1，但原运行根只有 ICU 66 数据。旧运行根中系统数字格式化器确实返回 NULL；在独立根导入本地恢复镜像的原版 `icudt78l.dat` 和 `icutzformat.txt` 后，157 项原生检查通过，包括四种 locale 的 36 次格式化／解析，以及真实 RSA 公钥导入、OpenSSL SHA256 签名验证和篡改拒绝。没有改写原版 CoreFoundation、Security 的转换与密码算法，也没有把错误强制变成成功。

直接修改 Darling `sigexc.c` 和 `abort_with_payload.c`，默认致命信号及 abort 改为只发送给当前进程，并完整重编译 879 个 libsystem_kernel 源文件。在私有进程组中实际终止 8 个测试子进程：旧版本的父进程和兄弟进程各收到 4 次 SIGSEGV、8 次 SIGABRT；新版本均为 0，子进程的真实致命退出仍保留。原版构建的 clang-stat-cache 后续加载失败也只终止该工具，父构建继续执行其他任务并正常报告退出码 65。早期 dyld 变体、默认停止信号、Darwin tracer 的组信号路径，以及忽略 SIGABRT 时的完整 abort 契约尚未验证或修复。

原版构建随后拒绝解析 Darling 的 `ProductBuildVersion=Darling`。本地参考用户态的原版 SystemVersion 元数据（26.6.2 / 25G83）已放入独立根。持久前缀会覆盖下层文件，因此实验启动器 `bin/darling-system-version` 在本次私有 mount namespace 的实际 overlay 视图绑定该文件；原 `bin/darling`、`bin/xcodebuild`、`scripts/runtime-ns.sh` 和持久前缀文件保持原样。原生读取测试确认私有视图与原版文件完全相同，并验证宿主前缀的 SHA 未变。这是 Linux 上的兼容用户态元数据，不表示宿主变成 macOS。

原版 SWBBuildService 的缺失依赖进一步通过完整原版 Intel OSLog（67 导出、11 个类）及 Swift OSLog overlay（13 导出）恢复。保留真实代码及后端调用；Swift overlay 使用显式的相对元数据恢复，未宣称完整 OSLog/logd 服务语义已验证。原版服务随后计算构建图和描述，运行目录及辅助文件任务；实际生成的 6 个 hmap、响应文件、构建请求与 manifest 已按 SHA 留存。原版 clang/ld 探测命令出现在构建日志中，尚无 CompileC/SwiftCompile 或成功链接证据。当前 ClangStatCache 任务失败于 CoreServices umbrella 缺失 `FSEventsGetCurrentEventId`；不能用关闭缓存或虚构事件 ID 来代替真实语义。CoreSimulator 服务不可用和构建目录 xattr 警告也仍存在。

```bash
python3 scripts/stage-icu-data-runtime.py
python3 scripts/test-icu-data-security.py
python3 scripts/test-icu-data-security.py --with-data
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/fatal-signal-kernel --variant-base runtime/icu-data-normal/darling-root --report artifacts/fatal-signal-kernel-build.json
python3 scripts/stage-fatal-signal-runtime.py
python3 scripts/test-fatal-signal-isolation.py
python3 scripts/test-fatal-signal-isolation.py --fixed
python3 scripts/stage-system-version-runtime.py
python3 scripts/test-system-version-binding.py
python3 scripts/rebuild-c-cache-image.py --target oslog-build-service-native --lazy-functions --analyze-code
python3 scripts/stage-swb-logging-runtime.py
python3 scripts/rebuild-c-cache-image.py --target swift-oslog-build-service-native --lazy-functions --experimental-swift --repair-swift-relative
python3 scripts/stage-swb-swift-logging-runtime.py
python3 scripts/probe-xcode-service-runtime.py version --swb-swift-logging --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --swb-swift-logging --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py build --swb-swift-logging --core-volume-diagnostic --cfprefsd-daemon --filecoordination --timeout-seconds 180
```

正常候选为 `runtime/swb-swift-logging-normal/`，工程测试使用独立的 `runtime/swb-swift-logging-diagnostic/` 宽松 CoreServices 策略；严格 Sandbox 构建仍未验证。证据：`artifacts/icu-signal-progress.json`；源码补丁：`artifacts/xnu-fatal-signal-isolation-source.patch`。最初错误的 namespace 过滤快照和会显著拖慢启动的全程 strace 没有用于证明编译成功；后续父子关系快照、精确故障捕获和原版任务输出构成进展证据。

## MobileAsset 真实查询与异步完成（前一补充）

对照原版 Intel MobileAsset 的 Objective-C 方法元数据、block 调用、结果码表和 XPC 请求代码，直接替换 Darling 的 MAAssetQuery 通用占位转发，完整重编译 MobileAsset 全部 15 个源文件并保留原有导出。实现类型／用途／过滤条件、原生 keyed archive 查询参数、真实 `com.apple.mobileassetd.v2` 同步请求、带类型校验的安全结果解码、资产属性／ID／状态与目录时间元数据；同时修正旧 MAAssetState 的猜测值。异步公开接口在 dispatch worker 执行真实同步请求，再到共享串行回调队列完成，当前没有实现原版 MAXpcManager 的完整异步任务管理。

查询服务不存在时，实际 libxpc 失效路径返回 MAQueryXpcError，不报告查询成功或虚构空资产。公开异步回调分别使用 `(MAQueryResult)` 和 `(MAQueryResult, NSError*)`；错误域与数值来自原版框架。取消通用无条件转发后，未知方法不会再静默吞掉调用。

原生测试通过 1,823 项检查，包含 48 次真实跨进程 XPC 查询／回复、4 个并发调用线程的 32 次异步查询、调用者释放查询对象及退出 autorelease pool 后的 8 次回调、非空／空结果、原生字段编码、查询错误、损坏回复与服务缺失。测试端是明确的本地协议对端，**不是 Apple mobileassetd，也不是资产下载服务**。两组既有 Pallas 实际传输／重试／生命周期回归均通过。原版 Xcode 两次重试均不再出现 MAAssetQuery 构造占位和 continuation 泄漏，记录了 Metal 工具链查询失败后的原版错误处理；没有跳过查询或改写 Xcode。

实时抓栈经 x86_64 fat slice 和 Mach-O segment 地址换算后，主线程位于 `DVTKVOConditionValidator waitForCondition`，调用方为 `_resolveInputOptionsWithTimingSection:`。其他线程分别在 SwiftPM `deriveMetalToolchainPath`／`waitUntilExit`、CoreSimulator `_loadValidCoreSimulatorService`、Security `_ucsp_client_verifyPrivileged2` 中等待。早期还观察到 CFPreferences 等待系统 cfprefsd。以上是实际位置证据，尚不能把任意一条后台等待断言为工程停滞的直接原因；下一步需记录子进程命令、管道及服务状态来建立因果链。

```bash
python3 scripts/analyze-mobileasset-query-protocol.py
python3 scripts/build-mobileasset-query-source.py
python3 scripts/test-mobileasset-query.py
python3 scripts/test-mobileasset-query-regressions.py
python3 scripts/probe-xcode-service-runtime.py version --mobileasset-query --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --mobileasset-query --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py build --mobileasset-query --core-volume-diagnostic --cfprefsd-daemon --filecoordination --timeout-seconds 180
python3 scripts/probe-mobileasset-query-xcode-stacks.py
python3 scripts/symbolicate-darling-stack.py --stem mobileasset-query-xcode-live --runtime-report artifacts/xcode-service-runtime-mobileasset-query-diagnostic-build-17adccbdf70e.json
```

候选 framework 在 `runtime/mobileasset-query-source/frameworks/`，通过单次进程的 framework 路径选中；运行时继续使用前一阶段同一组源码组件。原版 Xcode 和默认入口不变。证据为 `artifacts/mobileasset-query-progress.json`，源码补丁为 `artifacts/darling-mobileasset-query-source.patch`。本地资产目录 daemon、路径访问授权、实际下载、安装、完整原版异步任务管理、严格 Sandbox 和完整构建均未实现或未验证。

## XPC 激活失败与线程 materialization 策略（前一补充）

这些修复直接落在 Darling 源码，并完整重编译对应组件：libxpc 共 39 个编译单元，libsystem_kernel 共 879 个编译单元。libxpc 原有 630 个导出及 112 个重导出保留。bootstrap 查找失败过去让消息永久排队，现在通过实际连接取消流程向事件处理器和同步、异步调用者返回 INVALID 错误。两个真实不存在服务的测试由两次超时变为两次失效通知、同步与异步错误均正常返回；既有请求回复、取消生命周期、共享内存和损坏消息测试也通过。

Darling 的 iopolicysys 过去无条件返回成功，却没有保存或读取策略。现在通过私有线程 TSD 实际存储 DEFAULT/OFF/ON，并正确处理参数和 errno；1,066 项原生检查覆盖 8 个线程、512 次更新及线程隔离。进程范围策略、ORIG 修饰位、dataless 文件提供器和实际 hydration 尚未实现。

未修改的原版 Xcode 现可越过前述等待及策略断言；原版 filecoordinationd 日志记录了两次实际申请获准并执行。RunningBoard 服务仍缺失，此次修复让原版代码收到真实连接失败并执行自己的错误处理，没有实现进程监控，也没有宣称完整读写互斥已验证。下一处日志是 `MAAssetQuery initWithType:` 占位方法与 `downloadedAssets(assetType:attributesQuery:)` 泄漏 Swift continuation；尚未观察到 CompileC 或 SwiftCompile。

正常候选为 `runtime/materialize-policy-normal/`，保留严格 Sandbox 资源；工程诊断使用独立的 `runtime/materialize-policy-diagnostic/` 宽松 CoreServices 策略。原版 xcodebuild、默认入口及共享 server 构建输出保持原样。复现命令：

```bash
python3 scripts/build-libxpc-source.py --output-dir runtime/xpc-activation-source --report artifacts/xpc-activation-source-build.json --variant-base runtime/s2c-lifecycle-normal/darling-root
python3 scripts/stage-xpc-activation-runtime.py
python3 scripts/test-xpc-missing-service.py --xpc-activation --tag fixed
python3 scripts/test-xpc-activation-regressions.py
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/materialize-policy-kernel --variant-base runtime/xpc-activation-normal/darling-root --report artifacts/materialize-policy-kernel-build.json
python3 scripts/stage-materialize-runtime.py
python3 scripts/test-materialize-policy.py
python3 scripts/probe-xcode-service-runtime.py version --materialize-policy --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --materialize-policy --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py build --materialize-policy --core-volume-diagnostic --cfprefsd-daemon --filecoordination --timeout-seconds 180
```

证据：`artifacts/xpc-activation-materialize-progress.json`；源码补丁：`artifacts/libxpc-activation-failure-source.patch`、`artifacts/xnu-materialize-policy-source.patch`。旧运行根、原始失败日志和修改前输入按 SHA 保留。

## S2C 线程生命周期与原版文件协调服务（前一补充）

跟踪原版 CoreServices 证明，10 个挂载点已进入内部表，旧式卷引用按需分配。原生公开 API `FSPathMakeRef`、`FSGetCatalogInfo` 能为各挂载点生成真实引用；调用后原版 FileIDTree 与 CF 均返回 10 个卷，CF 枚举从 Cocoa 256 恢复为正常结束。无调试器运行也验证了这一结果。**这只是诊断：Xcode 的启动命令没有调用该程序预热卷引用，没有修改或强填内部卷字段。** 所有既有卷的启动发现仍待完善。

加载原版 CoreServices/configd/diskarbitrationd 后，曾在进入 Xcode 前卡住严格 UTI 预检。原生进程栈显示 UTI 等待 LaunchServices；LaunchServices 等待 CoreServices 的会话初始化；CoreServices 在 `mach_vm_map` 中等待远程 S2C 回复。读取真实 server 对象确认，目标是客户端进程 52 中已死亡的线程 62，回复信号量仍为等待状态。线程对象因未完成调用尚被保留，`weak_ptr::lock()` 成功不能代表 Linux 线程仍存在。

直接修复并重新构建 Darling server：先复制线程候选列表、释放进程锁，再排除死亡线程，并优先选择已在等待 RPC 回复的活线程；S2C 入口及取得串行信号量后再次拒绝死亡／正在终止的线程。没有改变原版 CoreServices、LaunchServices、Foundation 或 Xcode 的控制流。尚未宣称所有“请求已经发出后目标线程死亡”的取消竞态都已解决。

修复后，同一组原版服务下的严格 UTI 预检通过。原版 `filecoordinationd` 收到 Xcode 工程读访问申请，随后在 `NSFileAccessProcessMonitor` → `RBSProcessMonitor` → `RBSConnection` 的实际握手中等待缺失的 `com.apple.runningboard`。工程仍未进入编译。CoreSimulator 服务缺失也有原版日志，但当前不能把模拟器消息当作工程读取停滞的直接原因。

正常候选保留原严格 Sandbox 资源，原版 Xcode 版本和 SDK 列表通过。独立跨进程测试验证了向有工作线程的接收进程映射真实共享内存；32 轮内存入口生命周期、32 次并发映射、只读保护、128 轮电源与匹配通知释放回归均通过。正常根为 `runtime/s2c-lifecycle-normal/`，宽松 CoreServices 诊断根为 `runtime/s2c-lifecycle-diagnostic/`。默认入口、共享 server 构建输出和原版 Xcode 字节未更改。

```bash
python3 scripts/build-s2c-lifecycle-server.py
python3 scripts/stage-s2c-lifecycle-runtime.py
python3 scripts/probe-remote-vm-map.py --s2c-lifecycle --tag fixed
python3 scripts/test-s2c-runtime-regressions.py
python3 scripts/probe-xcode-service-runtime.py version --s2c-lifecycle --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --s2c-lifecycle --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py build --s2c-lifecycle --core-volume-diagnostic --cfprefsd-daemon --filecoordination --timeout-seconds 180
```

证据：`artifacts/s2c-lifecycle-progress.json`；源码补丁：`artifacts/darlingserver-s2c-lifecycle-source.patch`。前序运行根、源码版本及失败证据按原哈希保留。


## 挂载标志、规范路径和真实 VFS 通知（前一补充）

直接修改 Darling 源码并完整重建 879 个 libsystem_kernel 编译单元。Linux 的 `ST_VALID` 过去被直接当作 Darwin 的 `MNT_UNION`，导致原版磁盘服务跳过这些卷；现逐项转换挂载标志，并按文件系统类型标记已知本地卷和系统伪文件系统。根挂载设置 `MNT_ROOTFS`。虚拟宿主根边界返回的 `/Volumes/SystemRoot/` 规范为 `/Volumes/SystemRoot`；原版 DiskArbitration 使用 `getfsstat` 挂载列表与 `realpath` 精确匹配，额外的末尾斜杠此前导致对象创建失败。79 项原生检查覆盖实际 Linux 标志、Darwin 标志、路径、FSID 和挂载列表。

在 Darling notifyd 源码中接入 Linux `/proc/self/mountinfo` 快照比较，完整构建 7 个编译单元。初始快照只建立基线，不伪造挂载事件；实际新增、删除和选项变化才通过既有 Mach 通知通道发布。解析与差分通过 137 项 ASan/UBSan 检查。当前每 250 毫秒采样，可能漏过两次采样之间的短暂变化；XPC matching publisher 仍未实现。

端到端测试只在本次 Darling 的私有 user/mount namespace 中实际挂载 tmpfs、重挂载为只读并卸载，不修改宿主挂载表，也不通过 `notify_post` 制造测试事件。原生客户端通过 34 项检查；未修改的原版磁盘服务产生 11 次卷出现回调，为 `/`、`/Volumes/SystemRoot` 和末尾带斜杠的调用路径都返回非空真实描述。原版 configd 与磁盘服务在客户端结束后仍运行。**既有卷的启动发现尚未恢复，当前描述验证发生在真实挂载事件之后，不能据此宣称无需挂载活动即可完成初始化。**

原有生产对象匹配测试、128 次电源连接/订阅循环、7 组物理 OOL 消息和原生 FSEvents 设备测试在新运行库下回归通过。原版 Xcode 版本与 SDK 列表通过，工程构建在 40 秒上限内仍未进入 `CompileC`／`SwiftCompile`，包装进程最终为 -9，没有 xcodebuild 返回状态标记。正常运行根保留原严格 Sandbox 资源；另一个明确标记的宽松诊断根运行原版 CoreServices/configd/diskarbitrationd，真实服务端口已取得，但 FileIDTree 和 CF 卷枚举仍失败。限制性 Sandbox 执行、旧式卷引用及完整 FileCoordination 仍需实现。

```bash
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/mount-paths-kernel --variant-base runtime/iokitd-matching-runtime/darling-root --report artifacts/mount-paths-kernel-build.json
python3 scripts/build-notifyd-mounts-source.py
python3 scripts/stage-mount-flags-runtime.py
python3 scripts/test-mount-flags-native.py
python3 scripts/test-mountwatch-state.py
python3 scripts/test-real-mount-notifications.py
python3 scripts/test-mount-runtime-regressions.py
python3 scripts/probe-mount-volumes.py
python3 scripts/probe-xcode-service-runtime.py version --mount-flags --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --mount-flags --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py build --mount-flags --cfprefsd-daemon --filecoordination --timeout-seconds 40
```

补充证据：`artifacts/mount-flags-progress.json`；源码补丁：`artifacts/xnu-mount-flags-source.patch`、`artifacts/notifyd-mounts-source.patch`。正常候选为 `runtime/mount-flags-runtime/`。默认入口、共享 server 输出和原版 Xcode 可执行文件保持原字节。


## IOKit 匹配通知与原版 DiskArbitration 会话（前一补充）

完整重建 23 个 iokitd 源文件，补齐 x86_64 的 binary/XML/OOL 匹配订阅、匹配查询、属性条件、初始枚举、排空后重新启用通知、合并通知、首次匹配和终止队列。迭代器及订阅持有真实服务引用；服务注销后仍可通过已有队列或快照返回，最终释放时清理注册树的父子链接。

独立测试程序复用全部生产服务端对象文件，通过原生 SDK 客户端与实际 Mach 消息收发验证 11 次回调，覆盖注销后抑制排队回调、超过 4 KiB 的匹配条件、XML64、无效请求、接收队列满时的异步重试及释放。128 个订阅释放后，各自的 Mach 接收端口全部销毁；测试服务只存在于独立测试程序，不安装到正常运行根。Linux 介质发现和实际硬件热插拔尚未实现。

原版磁盘服务随后停在 `notify_register_mach_port("com.apple.system.kernel.mount", ...)`。Darling 安装配置未安装 notifyd 任务；恢复任务后，又发现 notifyd 的 Mach 通道在等待尚未实现的 XPC event publisher 初始回调。现完整构建 6 个 notifyd 源文件，在 publisher 不可用时连接实际 Mach 通道，保留 XPC 发布能力未实现的限制。任务仅安装到私有运行根并设为 0644。原生通知客户端通过跨进程发送、端口复用、取消和最终端口释放共 19 项检查；**未实现 XPC matching publisher 或 Linux 内核挂载事件生成**。

未修改的原版 `configd` 和 `diskarbitrationd` 现能持续运行。原版 DiskArbitration 客户端在有调试器、无调试器和默认守护进程模式下均成功创建会话并完成查询、调度及释放。当前 `/` 可创建磁盘对象，但磁盘描述为 NULL；`/Volumes/SystemRoot/` 磁盘对象为空，出现回调为 0。下一步是接入真实 Linux 介质、文件系统及挂载信息，恢复卷引用与 FileCoordination。

原有电源注册/释放循环、7 组物理 OOL 消息回归和原版 configd Dynamic Store 回归通过。新正常候选下，严格 UTI 预检、原版 `xcodebuild -version` 与 `-showsdks` 通过。原严格 Sandbox 资源、原版 Xcode、默认入口及共享 server 输出保持原样；完整工程编译、Unity/CocoaPods、归档、签名和导出仍未完成。

```bash
python3 scripts/build-iokitd-source.py --output-dir runtime/iokitd-matching-source --report artifacts/iokitd-matching-build.json
python3 scripts/build-notifyd-matching-source.py
python3 scripts/stage-iokitd-matching-runtime.py
python3 scripts/test-iokitd-matching.py
python3 scripts/probe-notify-matching-service.py
python3 scripts/test-iokitd-matching-regressions.py
python3 scripts/probe-diskarbitration-service.py --iokitd-runtime matching --configd --tag matching-default
python3 scripts/probe-xcode-service-runtime.py version --iokitd-matching --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --iokitd-matching --cfprefsd-daemon --timeout-seconds 40
```

证据：`artifacts/iokitd-matching-progress.json`；源码补丁：`artifacts/iokitd-matching-source.patch` 与 `artifacts/notifyd-matching-source.patch`。此前的电源、日志、Sandbox、FSEvents 和密码学证据保留并按原始哈希核对。

## Darling 源码电源服务与 Mach IPC（前一补充）

已从固定提交完整编译并替换私有运行根中的 `iokitd`，共 22 个编译单元，保留原 launchd 任务及服务归属。新增 Linux 恢复观察后端、`IOPower:/IOPowerConnection/IOPMrootDomain` 注册树、真实 Mach 用户连接与兴趣通知对象。未支持的电源控制接口继续返回错误。

同时修复 Darling server 的空物理复制 OOL 描述符：小缓冲区阈值为 0 时，原逻辑把空描述符误判为 VM 空间溢出，导致 `IOServiceOpen` 在到达服务端前返回 `0x400`。新增零长度处理，保留非空缓冲区原有复制路径。原生客户端验证 7 组混合端口/物理 OOL 消息，覆盖空、1 字节、8 KiB 边界及大缓冲区，确认复制后不受发送端修改影响。

补齐现代 IOKit 属性缓冲区接口，将数据写入经 Mach 审计确认的调用者任务；单属性查询返回原始值。原生 SDK 客户端通过电源注册、属性读取、跨任务打开拒绝、关闭状态检查；128 次连接和订阅循环后，实际守护进程接收端口数从活动时的 14 回到初始的 12，验证了最后发送权释放后的清理。

原版 `diskarbitrationd` 现已通过 `IORegisterForSystemPower`，下一处退出原因为 **could not create "media disappeared" notification.** 接下来需要实现 IOKit 设备匹配通知、迭代器及 Linux 媒体注册，仍不能创建完整的原版 DiskArbitration 会话或完成卷枚举。

**电源支持尚不完整。** 当前时钟后端只观察恢复，1016 项合成时钟测试通过 ASan/UBSan；尚未验证实际恢复消息经过原生回调，也没有实现休眠前确认/阻止机制。没有让宿主机休眠来测试。原严格 Sandbox 资源、原版 Xcode、默认入口及共享 server 构建输出保持原样；完整工程编译、Unity/CocoaPods、归档、签名和导出仍未完成。

```bash
python3 scripts/build-iokitd-source.py --output-dir runtime/iokitd-power-source --report artifacts/iokitd-power-build.json
python3 scripts/build-iokitd-power-server.py
python3 scripts/stage-iokitd-power-runtime.py
python3 scripts/test-iokit-power-service.py
python3 scripts/test-linux-resume-clock.py
python3 scripts/probe-xcode-service-runtime.py version --iokitd-power --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-xcode-service-runtime.py showsdks --iokitd-power --cfprefsd-daemon --timeout-seconds 40
python3 scripts/probe-diskarbitration-service.py --iokitd-runtime source --configd --debug --trace --tag power-domain-final
```

证据：`artifacts/iokitd-power-progress.json`；源码补丁：`artifacts/iokitd-power-source.patch` 与 `artifacts/iokitd-power-ipc-source.patch`。保留固定提交的基线构建和此前失败记录，主检查点仍为 `artifacts/native-crypto-progress.json`。

## 原版 configd 与日志组合接口（前一补充）

继续运行未修改的原版 `diskarbitrationd`，定位到它依赖原版 `configd` 的 Dynamic Store 服务。原版 configd 在进入主 CFRunLoop 前调用 `_os_log_send_and_compose_impl`，此前该接口是主动 abort 的兼容占位。

现在在 Darling libtrace 源码中实现发送/组合模式、原格式指针输出、调用者缓冲区与分配结果的所有权、errno 保存，并补齐 `os_log_pack_send_and_compose`。完整重建 9 个源文件；原兼容库通过已有 reexport 暴露真实源码实现，崩溃报告入口仍保留终止行为。2295 项检查通过，其中 192 组执行原版 Intel 包装函数的控制流，使用替代调用目标核对 ABI/标志传递；**这不是执行原版完整日志后端或证明全部日志语义一致**。既有 pack 269 项与 hook 1642 项回归通过。

原版 configd 现已进入并持续运行于原版 CFRunLoop。原版 SystemConfiguration SDK 客户端完成写入、读取、数据类型往返、删除及实际变更通知，16 项检查通过、收到 1 次通知；不是仅检查加载或返回非空对象。原版 diskarbitrationd 随后也成功创建 Dynamic Store 会话，但在 `IORegisterForSystemPower` 失败后退出 70。

独立探测确认：Darling 的 IOKit master 服务端口存在、通知接收端口可创建，但 `IOPower:/IOPowerConnection/IOPMrootDomain` 不存在，电源注册返回 0。已检出 Darling 固定引用的 iokitd 源码提交 `5549ac4cd2db923c256f016a1381b3bfb716730a`，下一步需要补电源域服务和真实事件订阅，再继续原版 DiskArbitration、卷枚举及 FileCoordination。没有填造电源对象或绕过原版守护进程的失败判断。

新正常候选保留原严格 SBPL 资源，原版 Xcode 版本、严格 UTI 和 SDK 列表回归通过。限制性 Sandbox、完整工程编译、Unity/CocoaPods、归档、签名、导出仍未完成；默认入口没有切换。

```bash
python3 scripts/build-libtrace-source.py --output-dir runtime/log-compose-source --report artifacts/log-compose-source-build.json
python3 scripts/stage-log-compose-runtime.py
python3 scripts/test-log-send-compose.py
python3 scripts/test-log-compose-regressions.py
python3 scripts/probe-diskarbitration-service.py --configd --log-compose --store-client --without-daemon --tag store-notification
python3 scripts/probe-diskarbitration-service.py --configd --log-compose --trace --debug --tag disk-after-configd
```

补充证据：`artifacts/diskarbitration-log-compose-progress.json`；源码补丁：`artifacts/libtrace-send-compose-source.patch`。原版 Xcode、原版 configd、原版 diskarbitrationd、默认入口和共享 server 输出保持原字节。

## 原版 Sandbox 的无约束策略与底层 FSEvents 设备（前一补充）

直接修改并重新编译 Darling server、libxpc 与完整 879 源文件的 libsystem_kernel。server 只接受经图遍历证明 198 个已知操作均允许的策略，并保留 fork/exec 状态；原版 CoreServices 的限制性策略仍返回 ENOTSUP。原版编译器对普通 `(allow default)` 仍注入四个拒绝项，不能把它当作完全允许。真实编译、附加、查询、通知及 fork/exec 的 SDK 测试通过 238 项，图证明通过 228 项，既有语义 6034 项和解析/变异 6488 项通过 ASan/UBSan。

原版 `coreservicesd` 在显式无约束策略的独立诊断根中完成 bootstrap 与系统会话后，曾因 `/dev/fsevents` 打开失败主动 abort。新增源码设备后端通过 Linux inotify 生成 XNU 格式的真实删除/重命名记录，处理重命名目标旧 inode、目录移动后的子项、设备排除列表及丢事件通知。使用真实 Unix 描述符传输，dup/fork/exec 和最终关闭沿用 Linux 生命周期。Linux 测试通过 337 项；Darling SDK 客户端通过 113 项，包含短读取不消费事件和错误参数检查。

原版服务现已完成设备打开和 CLONE ioctl，调试跟踪及无调试器运行各连续三次客户端检查后仍在运行，未修改服务或 xcodebuild 的可执行文件。但三个检查仍得到 FileIDTree 挂载点 0、Foundation 卷数组 nil。跟踪确认原版 `DASessionCreate` 返回 NULL，`_FSScheduleFileVolumeOperations` 返回 -36；这是接下来要处理的连接失败，不能据此认定它是卷枚举的唯一原因。

**诊断根替换了 CoreServices 的 SBPL 资源，只用于越过限制性策略阻塞定位后续问题，不作为生产候选。** 正常候选保留原严格策略资源。设备后端目前仅覆盖虚拟根中的删除/重命名，排除 Linux 伪文件系统；外部 SystemRoot 别名、其他事件类型、发起操作的 PID、硬链接标志和原内核完整语义仍未验证。原版 `xcodebuild -version`、严格 UTI 和带原版服务的 `-showsdks` 在新正常候选下回归通过。完整工程编译、Unity/CocoaPods、归档、签名和导出仍未通过，默认入口未切换。

```bash
python3 scripts/build-fsevents-device-server.py
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/fsevents-device-kernel --variant-base runtime/unrestricted-sandbox-runtime/darling-root --report artifacts/fsevents-device-kernel-build.json
python3 scripts/stage-fsevents-device-runtime.py
python3 scripts/test-fsevents-device-linux.py
python3 scripts/test-fsevents-device-native.py
python3 scripts/probe-fileidtree-service.py --fsevents-device --unrestricted-diagnostic --trace-after-session --paired-dirhelper --trace --repeat 3 --tag disk-arbitration
```

当前补充证据：`artifacts/unrestricted-sandbox-fsevents-progress.json`。增量源码补丁：`artifacts/darlingserver-fsevents-device.patch`、`artifacts/xnu-fsevents-device.patch`。此前运行根、构建输入和检查点的精确版本按 SHA 留存，避免用新源码冒充旧二进制的构建输入。

## 文件修改操作的 Sandbox 查询入口（前一补充）

在 Darling 内核兼容层源码新增查询与路径准备模块，接入 mkdirat、unlinkat、rmdir、renameat；rmdir 复用 unlinkat，避免漏掉删除路径。修改操作先完成查询，再调用实际 Linux 文件操作。父目录以 O_PATH 描述符固定，查询名由实际父目录和目标名称转换成 guest 路径；rename 分别检查源删除、目标创建及已有目标删除。参数复制有长度和可读性检查，失败时释放描述符，Quarantine 标记沿同一个父目录描述符执行。

完整编译 878 个源文件，保留原内核库导出，发布到独立运行根。正常文件操作通过 338 项检查；隔离的查询传输测试通过 251 项检查，记录 60 次查询，其中 39 次拒绝、2 次 Darwin EIO、1 次 Linux EAGAIN。被拒绝的创建、删除与替换未改变文件；相对路径、目录描述符、符号链接父路径、无效指针、过长路径及重复失败的描述符平衡均检查。测试还在查询期间将父目录改名并用指向另一目录的符号链接替换原路径，实际修改仍进入原来固定的目录。

负向测试只在单独的测试内核中替换查询传输这一编译单元；生产候选没有测试入口，查询继续交给真实 server。两者使用相同的文件操作源码。测试没有使用已附加的原版 SBPL 策略，因此不能据此声称完整策略已执行，也未验证与原版 macOS 内核逐项一致。

新运行根下，真实 Quarantine 标记、fork/exec、执行拒绝、进程代数、XPC、原版策略上传、`xcodebuild -version` 以及带原版服务的严格 UTI 和 `-showsdks` 回归通过。此次没有进行完整工程构建。**此历史候选的策略附加仍返回 ENOTSUP**；open/read/write、mmap/exec、元数据、扩展属性、link、Mach/XPC 等剩余路径还需要连接实际策略。原版 CoreServices、FileCoordination、Unity/CocoaPods、归档、签名、导出及默认 CI 入口尚未完成。

```bash
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/sandbox-fs-mutations-source --variant-base runtime/launchd-sandbox-source/darling-root --report artifacts/sandbox-fs-mutations-kernel-build.json
python3 scripts/stage-sandbox-fs-runtime.py
python3 scripts/test-sandbox-fs-mutations.py
python3 scripts/test-sandbox-fs-regression.py
python3 scripts/record-sandbox-fs-progress.py
python3 scripts/record-native-crypto-progress.py
python3 scripts/validate-native-sandbox-policy-checkpoint.py
```

测试编译单元替换的完整命令记录在 `artifacts/sandbox-fs-mutations-capture-kernel-build.json`，其运行根通过 `stage-sandbox-fs-runtime.py --capture` 发布，测试命令为 `test-sandbox-fs-mutations.py --capture`。当前补充是 `artifacts/sandbox-fs-progress.json`，源码补丁是 `artifacts/xnu-sandbox-fs-mutations-source.patch`。旧源码与构建输入按 SHA 保存，原版 xcodebuild、共享 server 构建输出和默认入口未改动。

## launchd Sandbox 查询源码接通（前一补充）

直接修改 Darling launchd 的构建条件，实际启用此前被 `DARLING` 宏关闭的 Sandbox 检查。完整编译 16 个源文件，新二进制确实导入 `sandbox_check_by_audit_token`；11 处调用从 PID 查询改为使用 Mach 消息中的调用方 audit token，包含进程执行代数，并将查询错误和拒绝均作为非零结果拦截。

全局和按 PID 的服务注册、未知服务 check-in、查询、实际发送权与接收权传递、fork/exec 后身份通过 144 项真实运行检查。隔离的测试查询传输对指定服务注入 6 次拒绝和 6 次 EIO，34 条查询日志核对了实际调用者 PID、执行代数与全局/本地选择器；104 项路由检查通过。使用同一个测试传输的旧 launchd 对照跳过查询，在要求拒绝时仍接受注册。注入只存在于独立测试运行目录，生产候选使用原来的真实 Sandbox 查询库；这些负向测试不证明 SBPL 策略已附加或已生成真实拒绝决定。

原版 `xcodebuild -version`、严格 UTI 及带原版偏好和 LaunchServices 服务的 `-showsdks` 均通过；真实 XPC 的 16 次连接、256 次回复以及原版策略的 29 次上传、216 项检查通过。直接 `-showsdks` 未启动所需服务时的超时保留为对照，测试配置已恢复所需服务。此次没有再次运行完整工程构建，未修改原版 xcodebuild 和默认 CI 入口。

**原版策略附加仍返回 ENOTSUP。** 这一步接通的是 launchd 的查询执行路径；XPC 域的现有查询例外、server 中的进程策略状态及文件、mmap/exec、POSIX IPC、进程和 sysctl 等权限检查仍需实现。原版 CoreServices、卷引用号、FileCoordination、工程编译、Unity/CocoaPods、归档、签名和导出均未声称完成。

```bash
python3 scripts/build-launchd-sandbox-source.py
python3 scripts/build-launchd-sandbox-capture.py
python3 scripts/stage-launchd-sandbox-capture-baseline.py
python3 scripts/test-launchd-sandbox.py
python3 scripts/test-launchd-sandbox.py --baseline
python3 scripts/test-launchd-sandbox.py --capture
python3 scripts/test-launchd-sandbox-regression.py
python3 scripts/record-launchd-sandbox-progress.py
python3 scripts/record-native-crypto-progress.py
python3 scripts/validate-native-sandbox-policy-checkpoint.py
```

当前补充报告是 `artifacts/launchd-sandbox-progress.json`，增量源码补丁是 `artifacts/darling-launchd-sandbox-audit-source.patch`。历史构建、未启用查询的旧二进制及源码输入均保留。

## 原版 Sandbox 字节码与 server 上传入口（前一补充）

直接在 Darling server 源码中加入原版 Intel Sandbox 决策图和字符串匹配字节码解释器，并接入原版 `sandbox_apply` 使用的 MAC 操作 0 上传入口。原版编译器实际生成的 26 份策略通过 6,034 项语义检查，26 份有效程序、3,462 项损坏输入及 3,000 项确定性变异通过 ASan/UBSan 检查。操作表的 198 个名称和 105 个非空过滤器记录从当前原版编译器提取；其中 system-attribute 的 apple-internal 与 sandbox-debug-mode 是不同条件，不能沿用第三方反编译器的旧标签混为一谈。

独立完整 server 构建已启动并运行原版 SDK 客户端。29 次原版有效字节码上传实际到达解释器，包括现场编译的 CoreServices profile；坏指针、损坏输入及失败后保持原进程状态等共 216 项检查通过。未修改的原版 `coreservicesd` 也经 gdb 和 server 日志确认到达同一入口，其 37 节点策略成功解码。

**策略实际应用与操作权限检查尚未实现。** 有效上传目前明确返回 ENOTSUP，不附加策略，不报告应用成功；原版 `coreservicesd` 仍退出 1，尚未完成 bootstrap。解释器只支持当前固定 Intel 格式及已测试过滤器子集，路径上下文仍需要由实际 vnode/描述符解析；容器、扩展、完整 Unicode 规则和其他版本未声称支持。没有进行新的完整 Xcode 工程构建。下一步是连接文件、mmap/exec、Mach、POSIX IPC、进程及 sysctl 等操作的真实权限检查，再恢复共享卷服务和 FileCoordination。

该阶段检查实际编译条件确认，当时选用的 Darling launchd 将 `HAVE_SANDBOX` 设为 0，二进制没有导入 `sandbox_check`；源码中 11 处检查因此未编入。这一发现是上面 launchd 查询源码修复的依据。

```bash
python3 scripts/build-sandbox-policy-vm-server.py
python3 scripts/test-native-sandbox-policy-vm.py
python3 scripts/test-native-sandbox-policy-parser.py
python3 scripts/test-native-sandbox-policy-upload.py
python3 scripts/probe-fileidtree-service.py --policy-vm --paired-dirhelper --trace --tag upload-decoded
python3 scripts/record-native-sandbox-policy-progress.py
python3 scripts/record-native-crypto-progress.py
```

当前补充报告为 `artifacts/native-sandbox-policy-progress.json`，源码补丁为 `artifacts/darlingserver-sandbox-policy-source.patch`。旧源码输入与检查点已按 SHA 保存，原 server 构建输出已恢复；原版 xcodebuild 和默认 CI 入口未改动。

## CoreServices 目录初始化源码修复（前一补充）

实时 gdb 跟踪修正了“本地设备表为空”的初始推测：原版 CarbonCore 成功把根卷加入本地 FSNode universe，但其旧式卷引用号（设备记录 +0x4c）仍为 0，随后被原版 FileIDTree 挂载点枚举过滤。原版 `_FSNode_SetVolumeRefNumInternal` 是该字段的赋值入口；没有修改这个字段或跳过过滤条件。相关指令与现场在 `artifacts/fileidtree-local-volume-reference-analysis.json`。

未修改的原版 `coreservicesd` 已加入独立探测。最初它在初始化缓存目录时退出：旧 Darling `_dirhelper` 只拼接 HOME/.cache/服务名，却不建立父目录。直接修复 `src/libsystem_coreservices/dirhelper.c`，实际创建所需的 guest home、缓存基目录和服务目录，检查截断、已有普通文件等真实错误，并持有后缀字符串的副本。完整编译该组件全部 3 个源文件，保留原先 8 个导出，使用独立运行目录。旧源码对照在目录不存在时失败；新源码通过 156 项实际目录、权限、错误、后缀生命周期及全新 HOME 检查。这仍采用 Darling 原有 HOME/TMPDIR 路径布局，未声称实现 Apple 的完整用户 UUID 目录分配协议。

目录修复后的原版 daemon 越过了临时/缓存路径解析。进一步对照证实：最初的 “No such file or directory” 来自原版 Sandbox 包装层调用 Darling 编译器 stub 时，`sandbox_create_params` 返回 NULL 却保留了旧 errno；它不能证明 profile 文件访问失败。实际选中的包装层是原版库，不能把未选中的 Darling `sandbox_init_with_parameters` stub 当作这次故障的调用点。

随后恢复原版 Sandbox 编译器（36 导出）及 Match 引擎（13），没有替换编译或策略应用调用。只把 typed-malloc 导入转到已验证的 Apple 分配器回退实现，并让编译器使用原版 Sandbox 的通知入口。原版编译器已实际编译简单策略、带参数的策略，并拒绝未知操作与语法错误；旧编译器对照在参数分配阶段即返回 NULL。使用与原版调用方一致的延迟绑定；立即绑定仍暴露 LoggingSupport 中缺失的 `__dyld_dlsym_blocked`，未声称整个依赖闭包立即绑定通过。

在独立运行根导入 533 个未修改的原版 Sandbox 资源文件后，gdb 确认原版 `coreservicesd` 的参数创建及真实命名 profile 编译均成功。其下一步 `sandbox_apply` 调用实际返回 -1 / Operation not supported：当前服务端只实现 Sandbox 查询，尚不执行策略应用操作。服务因此退出 1，尚未进入 bootstrap check-in，客户端仍等待。这次没有进行新的完整 Xcode 工程构建，策略执行、卷引用号、共享设备表和 FileCoordination 仍需完成；默认 CI 入口未切换。

```bash
python3 scripts/build-coreservices-directories-source.py --baseline
python3 scripts/build-coreservices-directories-source.py
python3 scripts/test-coreservices-directories.py --baseline
python3 scripts/test-coreservices-directories.py
python3 scripts/probe-sandbox-compiler-native.py --baseline
python3 scripts/probe-sandbox-compiler-native.py
python3 scripts/stage-sandbox-compiler-resources.py
python3 scripts/probe-fileidtree-service.py --trace --paired-dirhelper --sandbox-resources --tag original-compiler
```

## 源码修复、原版密码库与 FileCoordination（当前阶段）

实现方式包含三部分：直接修改并重编译 Darling 源码；从原版 Intel 映像恢复必要库的代码、重定位与元数据；通过私有 DYLD 路径选择候选库，并对个别不兼容的导入做符号重定向。因此当前并非只通过 hook 实现，也并非所有变更都已整合成一套完整的 Darling 源码构建。原版 xcodebuild 二进制 SHA 保持不变，默认 CI 入口尚未切换。

Darling CoreCrypto 源码已实现 HKDF、修复 HMAC 长密钥处理、补齐 AES-CTR 与 SHA3-224/256/384/512，并使用固定版本 BoringSSL 实现 X25519/Ed25519。完整编译全部 56 个源文件，保留原先 402 个导出；其他原有 stub 未声称补齐。源码候选与原版 CoreCrypto 分别通过 HKDF/HMAC 210、CTR 81、SHA3 236、25519 113 组独立对比，各 640 组。原版接口不测试违反 nonnull 前提的调用；原版与旧 Darling 的 CTR 私有结构回调顺序不同，测试客户端按各自 ABI 调用，未重写原版运行库结构。

当前构建候选选用匹配的原版 CoreCrypto（1,088 导出）、CommonCrypto（245）、CryptoKit（1,823）、C 桥（29）、CryptoTokenKit（207）。密码算法调用未重写；CoreCrypto/CommonCrypto 的 `_malloc_type_malloc` 导入转到 Apple 原始 typed-malloc 回退源码独立编译的轻量库，仅依赖底层分配器与 dyld。Darling 源码另补入原版 Security、Token 和 LocalAuthentication 常量；17 个实际 CFString 的类型、值、长度及复制验证通过，未实现硬件 Secure Enclave 或认证成功逻辑。

原版 Apple SDK 编译的 CryptoKit 客户端通过 11 项独立结果验证，覆盖 P256、X25519、Ed25519、AES-GCM、ChaChaPoly、SHA256、SHA3、HMAC、HKDF，并验证签名篡改和错误认证标签被拒绝。原版 AppleArchive C/Swift/Compression 完成 none、zlib、lz4、lzfse 各 65,537 字节压缩往返和 AEA 对称加解密，拒绝错误密钥与密文篡改。完整归档目录处理、全部 API 及全部加密 profile 尚未验证。进程身份、Sandbox、C++ 异常、分配器和 CoreUtils 回归通过，其中 CoreUtils 为 852 组、13,385,084 项检查。原版 CoreCrypto 缺少旧 Darling 导出的 28 个私有符号，尚需在旧消费者真实调用时审查兼容性。

原版构建已越过先前的密码库加载失败。实时堆栈显示主线程在 NSFileCoordinator 等待工程文件的协调读取；Darling 自带 filecoordinationd 的自定义协议不能处理原版 Foundation 的 NSXPC 消息。改为启动未修改的原版 daemon 后，确认实际选中了该程序，但仍反复记录卷枚举错误并重启。原版 NSFileManager、CoreFoundation、CarbonCore 才是当前选中的实现，不能通过修改未选用的 Darling NSFileManager nil stub 修好此问题。下一步追踪 FileIDTree/FSNode universe 的设备表初始化与更新，恢复真实服务及文件系统行为。BSD 普通与可重入挂载查询均返回 10 项，尚不能据此认定上层挂载点表已正确建立；守护进程退出的完整原因也未确认。

最后一次构建未出现 CompileC/SwiftCompile，外层超时终止返回 -9；清理期间记录原版状态码 132。没有把此状态当作编译成功，也没有绕过文件协调或伪造认证结果。

```bash
python3 scripts/test-corecrypto-hkdf.py --native
python3 scripts/test-corecrypto-ctr.py --native
python3 scripts/test-corecrypto-sha3.py --native
python3 scripts/test-corecrypto-25519.py --native
python3 scripts/test-cryptokit-original.py
python3 scripts/test-native-crypto-constants.py
python3 scripts/test-applearchive-native.py --native-crypto
python3 scripts/test-native-crypto-regression.py
python3 scripts/probe-native-volumes.py
python3 scripts/probe-xcode-service-runtime.py build --filecoordination --cfprefsd-daemon --timeout-seconds 120
python3 scripts/record-native-crypto-progress.py
```

以上会话驱动必须依次运行，不能并发操作同一 Darling 环境。上一检查点 347 个证据、状态和脚本文件存档于 `artifacts/archive-crypto-history/manifest.json`；旧源码输入另有显式快照。以下章节保留历史阶段记录。

## libdispatch workloop 与 libxpc 接收权生命周期（上一阶段）

直接修改 Darling libdispatch 源码：关闭内核 workloop 后端时，普通 pthread 根队列运行 workloop，需要在调用期间设置当前 workloop 并恢复原上下文。原版 lsd 的旧现场在 `_dispatch_lane_serial_drain+0x5f9` 解引用匿名标记 `-4`。完整编译 32 个源文件，保留全部 654 个导出。旧库对照失败，新库通过 1,024 个真实异步任务、FIFO/串行性、两层目标队列、同步及 async-and-wait 嵌套调用、当前上下文恢复和独立根队列检查。测试遵照原有 SPI 说明：dispatch_sync 不采用目标 workloop 的当前上下文，async-and-wait 才采用。

之后捕获 lsd 的独立 SIGILL，位置是 `_dispatch_mach_recv_direct_merge_evt+0x26` 的端口消失断言。实时 gdb 记录 libxpc 释放端口 7683 的接收权，随后同一个端口触发 EV_VANISHED。进一步核对后排除了“普通事件回传注册标记”的初始推测：选用的 libkqueue 已清除该注册位，陷阱参数 2 是 DISPATCH_MACH_RECV_MESSAGE 常量，也不是队列消息数。原始现场、修正后的解析及推理在 `artifacts/xpc-sent-message-ownership-analysis.json`。

真正的问题在 libxpc 的发送成功回调：DISPATCH_MACH_MESSAGE_SENT 落入默认分支，执行 mach_msg_destroy，重复消费已经由发送操作移交的 MOVE 权利和 OOL 资源。同一进程连接自身服务时，移交后的接收权仍位于同一任务内，会被再次销毁。源码为该成功事件增加明确分支，不再销毁消息内容，消息对象继续管理自身缓冲。完整编译 39 个 libxpc 源文件，保留之前选用版本全部 640 个导出。真实 XPC endpoint 同进程测试中，旧库无法完成首次正常回复；新库通过 16 次连接建立、256 次独立载荷请求/回复及取消流程。原版工程构建随后正常返回 70，且结束前 lsd 仍在运行；这不代表所有服务生命周期路径均已验证。

DiskManagement 的缺失入口也通过源码补齐。独立读取实际 Intel 缓存确认，原版 DMNSError 的完整函数仅有 `push rbp; mov rsp,rbp; xor eax,eax; pop rbp; ret` 八字节，即忽略参数并返回 nil。新增源码完整重编译该框架 23 个文件，补入函数的全部指令与原版相同；其他 DMManager 等通用磁盘操作 stub 原样保留，未声称实现挂载、分区或错误转换。

最新运行库下，严格 UTI、原版版本/SDK 查询、进程身份、Sandbox、C++ 异常、分配器/替换分配器、CoreUtils 密码算法以及 MobileAsset Pallas 真实 XPC 传输回归均通过。原版构建当前缺的是 DVTDownloads 使用的 AppleArchive Swift 解密流接口，现有 AppleArchive overlay 仅实现部分文件流；没有用 nil 解密流或虚假的认证成功消除这个错误。接下来补齐真正的归档/解密接口及依赖，再继续原版工程。

```bash
python3 scripts/build-dispatch-workloop-source.py
python3 scripts/test-dispatch-workloop-context.py --baseline
python3 scripts/test-dispatch-workloop-context.py
python3 scripts/build-diskmanagement-nserror-source.py
python3 scripts/build-libxpc-source.py --output-dir runtime/xpc-sent-message-source --variant-base runtime/dispatch-workloop-source/darling-root --report artifacts/xpc-sent-message-source-build.json
python3 scripts/stage-xpc-sent-message-runtime.py
python3 scripts/test-xpc-loopback-sent.py --baseline
python3 scripts/test-xpc-loopback-sent.py
python3 scripts/test-xpc-sent-message-regression.py
python3 scripts/test-xpc-sent-mobileasset.py
python3 scripts/probe-xcode-service-runtime.py --sent-messages --cfprefsd-daemon --mdns-library-only --timeout-seconds 40 version
python3 scripts/probe-xcode-service-runtime.py --sent-messages --cfprefsd-daemon --timeout-seconds 40 showsdks
python3 scripts/probe-xcode-service-runtime.py --sent-messages --cfprefsd-daemon --timeout-seconds 120 build
python3 scripts/record-dispatch-xpc-progress.py
```

三份源码补丁在 artifacts：`darling-libdispatch-workloop-context-source.patch`、`darling-libxpc-sent-message-source.patch`、`darling-diskmanagement-nserror-source.patch`；反向应用检查通过。原版 Xcode 二进制及默认 CI 入口未改动。前一检查点的 3,219 个文件按内容 SHA 存档于 `artifacts/cryptex-workqueue-history/manifest.json`，旧运行库与源码输入保留；以下内容是历史阶段记录。

## 原版 Cryptex/LibreSSL 与 Darling 工作线程栈修复（前一阶段）

从 Intel 缓存恢复七个原版映像：三个 Cryptex 库、libauthinstall、libcrypto.42、TrustEvaluationAgent 和 libswiftSystem_Foundation。新运行库下分别执行 dlopen 均成功；没有重定向这些映像的后端调用。Swift/Foundation 桥本来就是没有函数和显式导出的 Foundation 重导出映像，保留原有 LC_REEXPORT_DYLIB，未用自行创建的空库替代。加载成功不证明认证协议、Cryptex 挂载或 TrustEvaluationAgent 服务已经实现。

libcrypto.42 的 3,447 个原版导出保留。其手写汇编数据依据 OpenBSD 官方 LibreSSL 2.6.5 源码逐字节核对：10 段、17,696 字节常量，48 个实际读取引用及四个原版数据符号；9 种损坏/错误分类对照均被拒绝。输出映像里的这些字节保持不变。真实原版 AES、VPAES、BSAES、Camellia、SHA、Whirlpool、4-bit/CLMUL GHASH 通过 196 组独立向量、369,361 项检查；参考来自 Linux OpenSSL 3、hashlib 和独立位串乘法。这些测试不覆盖全部导出或证书信任。

Darling MobileAsset 完整编译 15 个源文件，保留原先 82 个导出并增加两个从原版核实的 NSString 属性名：`ASAttributeDownloadSize = _DownloadSize`、`ASAttributeUnarchivedSize = _UnarchivedSize`。现有 Pallas 客户端的真实 XPC 请求/回复、并发、连接重试和错误路径回归通过；其他通用资产 API 的旧 stub、真实下载服务和安装逻辑仍未实现。补丁为 `artifacts/darling-mobileasset-download-attributes-source.patch`。

原版 Xcode 的 SIGSEGV 现场显示，工作线程反复复用时保留了旧 libpthread/syscall 栈帧。直接修复 XNU 兼容层 `wqueue_entry_point_asm_jump`，从 pthread 对象读取正确的栈顶，重置 x86_64 rsp、16 字节对齐并清除旧帧链，再进入原有工作线程入口。完整重新编译 libsystem_kernel 的 877 个源文件。旧库对照第 50 次复用已经增长 16,464 字节；新库同一线程 2,048 次复用的栈跨度为 0，真实空闲超时及 pthread 析构也通过。进程身份、Sandbox、C++ 异常、分配器、替换分配器及 CoreUtils 密码回归均通过。补丁为 `artifacts/xnu-workqueue-stack-source.patch`。

最新原版工程构建经过严格 UTI，正常返回 70，实际报错是 DVTDownloads 引用的 DiskManagement `_DMNSError`。另外捕获 lsd 的真实 SIGSEGV：libdispatch 的 `_dispatch_lane_serial_drain+0x5f9` 在 workloop QoS 比较时解引用匿名 workloop 标记 `-4`，访问地址 `0x38`。Darling 的构建关闭了内核 workloop 后端，下一步要修复源码中的回退执行上下文，并验证真实请求回复与 lsd 生命周期。证据在 `artifacts/lsd-workloop-crash-analysis.json`；没有把服务退出 139 当作通过。

```bash
python3 scripts/prepare-crypto42-source-literals.py
python3 scripts/rebuild-c-cache-image.py --target crypto42-device-native --analyze-code --lazy-functions
python3 scripts/test-source-assembly-literals.py
python3 scripts/stage-cryptex-native.py
python3 scripts/build-mobileasset-download-attributes.py
python3 scripts/test-crypto42-native.py
python3 scripts/test-mobileasset-download-attributes.py
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/workqueue-stack-kernel-source --variant-base runtime/quarantine-vfs-kernel-source/darling-root --report artifacts/workqueue-stack-kernel-source-build.json
python3 scripts/stage-workqueue-stack-runtime.py
python3 scripts/test-workqueue-stack-reuse.py --baseline  # 验证旧库的已知失败
python3 scripts/test-workqueue-stack-reuse.py
python3 scripts/test-workqueue-stack-regression.py
python3 scripts/probe-cryptex-native.py --workqueue-stack
python3 scripts/probe-xcode-service-runtime.py --workqueue-stack --cfprefsd-daemon --mdns-library-only --timeout-seconds 40 version
python3 scripts/probe-xcode-service-runtime.py --workqueue-stack --cfprefsd-daemon --timeout-seconds 40 showsdks
python3 scripts/probe-xcode-service-runtime.py --workqueue-stack --cfprefsd-daemon --timeout-seconds 120 build
python3 scripts/record-cryptex-workqueue-progress.py
```

原版 Xcode 二进制 SHA 未变。旧运行库保留，修改前的输入按内容 SHA 存档供旧构建校验，新运行库单独校验当前源码。前一检查点的 358 个文件、初次 Cryptex 试验及后续构建尝试均有独立历史归档；以下内容为历史阶段记录。

## DeviceIdentity、真实 IOKit 入口及 Image4 别名（前一阶段）

从本地原版 Intel 缓存恢复 DeviceIdentity、MultiverseSupport、libbootpolicy 和 libimage4，保留原始代码和需要的 bundle 资源，共 402 个原版导出。原有 RemoteXPC 和 RemoteServiceDiscovery 继续复用先前已验证的版本。上述新库均没有替换策略、认证或设备后端；直接加载 DeviceIdentity 和 `/usr/lib/libimg4.dylib` 均已实际成功，但未验证设备证明或所有库函数。

Darling 源码新增 `IOMainPort`，依据原版 Intel 指令直接转发到 `IOMasterPort`；源码、头文件和 CMake 均已接入。当前以独立源码组件编译并保留原有 IOKit 后端，未宣称完整重编译 IOKit。实际测试中，新旧入口均返回同一个真实发送端口，非法 bootstrap port 得到同一个原始错误；端口类型、引用释放和原有 IOServiceMatching 查询也通过。Security 源码增加私有常量、声明和导出项，值 `2147483680` 来自原版 CFString 数据；CryptoTokenKit 源码补 `TKErrorDomain`，原版值为 `CryptoTokenKit`。两个对象的运行时 CFString 类型和值均验证通过，未实现 Secure Enclave 或 Token 服务。

恢复函数的正常延迟绑定后，DeviceIdentity 可以加载。另一个保持立即绑定的独立原版代码对照，仍明确报告缺少 `SecKeyCopySystemKey`。因此不能把加载成功说成所有 Security 私有接口都已实现；原版调用实际走到这些接口时仍需继续补齐。

Image4 的路径依据另行获取、通过 Apple chunklist 验证的官方 Intel 恢复镜像：macOS 15.4.1（24E263）中的 `usr/lib/libimg4.dylib` 实际是指向 `./libimage4.dylib` 的符号链接。当前使用本地 macOS 26.6.2 Intel 缓存恢复的原版 libimage4，并还原该兼容入口。该镜像仅在 Linux 上读取文件。此前对当前安装包全部 53 个 payload 的搜索未找到这个别名，搜索与真实链接记录均保留在 artifacts。

工程的下一项依赖是 Cryptex。其三个原版库和 libauthinstall 的代码恢复候选已生成，尚未选用；完整依赖还需要 libcrypto.42。后者在 8 类手写汇编区域出现 58 个未分类引用和 49 条指令诊断，疑似将嵌入的常量表当成了代码；当前分析器拒绝输出运行库。已从 OpenBSD 官方取得对应的 LibreSSL 2.6.5 macOS 汇编源码，下一步逐字节匹配 AES、Camellia、GHASH、SHA 和 Whirlpool 的常量表，并验证其边界与代码引用，再恢复、测试真实密码实现和 Cryptex 依赖。没有用空库或虚假的认证结果消除加载错误。

```bash
python3 scripts/build-iokit-main-port-source.py
python3 scripts/build-security-device-constant.py
python3 scripts/build-crypto-token-error-source.py
# 原版缓存恢复命令示例；四个选用目标均采用 --analyze-code --lazy-functions
python3 scripts/rebuild-c-cache-image.py --target image4-device-native --analyze-code --lazy-functions
python3 scripts/stage-device-identity-native.py
python3 scripts/probe-device-identity-native.py
python3 scripts/probe-device-identity-native.py --image4
python3 scripts/probe-device-identity-native.py --eager-control  # 预期捕获未实现的真实 Security 接口
python3 scripts/test-device-loader-source-components.py
python3 scripts/test-device-identity-regression.py
python3 scripts/probe-xcode-service-runtime.py --device-identity --cfprefsd-daemon --mdns-library-only --timeout-seconds 40 version
python3 scripts/probe-xcode-service-runtime.py --device-identity --cfprefsd-daemon --timeout-seconds 40 showsdks
python3 scripts/probe-xcode-service-runtime.py --device-identity --cfprefsd-daemon build  # 当前 70，缺少 Cryptex
python3 scripts/record-device-identity-progress.py
```

当前版本/SDK 查询及真实进程、Sandbox、C++ 异常、分配器和密码向量回归均通过。源码补丁为 `artifacts/darling-iokit-main-port-source.patch`、`artifacts/darling-security-device-constant-source.patch` 和 `artifacts/darling-crypto-token-error-source.patch`，反向应用检查通过。前一阶段 140 个证据、脚本、状态及原版组件文件归档到 `artifacts/quarantine-vfs-history/manifest.json`。以下章节保留历史阶段记录，以当前检查点判断最新状态。

## Quarantine 文件策略、原版 cfprefsd 与 Xcode 初始化（前一阶段）

这部分直接修改 Darling server 和 libsystem_kernel 源码，并完整编译后者的 877 个源文件。新增真实进程策略状态、fork/exec 继承、文件创建/写打开/重命名/硬链接的 Quarantine 属性传播、属性修改限制，以及 exec/posix_spawn 执行检查。文件标记实际存入 Linux `user.com.apple.quarantine`，宿主读取验证持久内容；没有仅保存进程 token 就确认策略应用成功。旧内核搭配新服务端的对照仍拒绝应用策略。

原版 Intel Quarantine 的本地机器码是行为依据；进程 setprocinfo 的第 9 个 64 位槽（偏移 64）才是 flags。`flags=6` 的策略已覆盖当前测试中的普通文件、目录及继承行为。创建文件带 `0x86`；重命名清除 hard 位后为 `0x82`；受该策略限制的进程删除属性后会重新标记；带 hard 位的 Mach-O 在 exec 和 posix_spawn 下均被拒绝，包括 hard+approved 组合。测试另覆盖合法/畸形属性、属性前缀别名隔离及无策略父进程对照。未知 flags、追踪、排除模式、跨进程策略控制和实际 Seatbelt profile 仍未实现；Linux 符号链接属性和完整 xattr/listxattr 命名空间兼容也未完成。

真实 cfprefsd 已越过先前的策略应用失败，实际接收并回复 CFPreferences 请求；严格 UTI 的类型、扩展名、归属检查均通过。原版 `xcodebuild -version` 返回 `Xcode 26.6 / Build version 17F113`，`-showsdks` 列出 iOS/macOS 等 26.5 SDK 并返回 0。守护进程日志中的 Seatbelt 初始化错误仍保留，未把未实现的 profile 当作已应用。部分工程探测结束时 lsd 的 LastExitStatus 为 139，仍需追踪其生命周期失败。

工程构建进一步触发了未实现的 `quotactl`（165）。新增源码将 GETQUOTA、QUOTASTAT、SYNC 转换到 Linux `quotactl_fd`，根据真实后端结果返回配额信息或错误；当前文件系统不支持配额，验证得到 Darwin EOPNOTSUPP（102）。不存在路径、无效指针、类型及未支持的配额修改命令也已验证。配额开启的文件系统尚未运行验证，未假造零配额或无限磁盘空间。修复后工程构建正常返回 70，明确报告所缺的插件依赖，尚未调用编译器。

DeviceIdentity 的原版 Intel 缓存代码和原版 bundle 资源已单独恢复：90 个导出、74 个 Objective-C 方法，未替换其认证后端。加入原版 libbootpolicy 后，直接加载仍报告缺少 MultiverseSupport；这一试验位于单独 profile，尚未并入通过版本/SDK 查询的运行库。下一步补齐实际依赖后继续原版工程构建，不跳过必须加载的模拟器插件，也不生成虚假的设备身份或信任结果。

```bash
python3 scripts/build-quarantine-vfs-server.py
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/quarantine-vfs-kernel-source --variant-base runtime/crypto-quarantine-runtime/darling-root --report artifacts/quarantine-vfs-kernel-source-build.json
python3 scripts/stage-quarantine-vfs-runtime.py
python3 scripts/test-quarantine-vfs-source.py
python3 scripts/test-quotactl-source.py
python3 scripts/test-quarantine-vfs-regression.py
python3 scripts/probe-xcode-service-runtime.py --quarantine-vfs --cfprefsd-daemon --mdns-library-only --timeout-seconds 40 version
python3 scripts/probe-xcode-service-runtime.py --quarantine-vfs --cfprefsd-daemon --timeout-seconds 40 showsdks
python3 scripts/probe-xcode-service-runtime.py --quarantine-vfs --cfprefsd-daemon build  # 当前 70，缺少 DeviceIdentity
python3 scripts/probe-device-identity-native.py  # 独立试验：当前缺少 MultiverseSupport
python3 scripts/record-quarantine-vfs-progress.py
```

进程身份（106 项）、Sandbox 查询（95 项）、C++ 异常（3215 项）、分配器（251 项）、替换分配器（331 项）及密码算法（852 组独立向量、13,385,084 项检查）在新运行库下全部通过。三个源码补丁 `darlingserver-quarantine-vfs-source.patch`、`xnu-quarantine-vfs-quota-source.patch`、`darling-quarantine-vfs-companions-source.patch` 位于 artifacts，反向应用检查通过。前一阶段 86 个证据、脚本及状态文件按内容 SHA 归档到 `artifacts/coreutils-quarantine-history/manifest.json`。以下章节保留历史阶段记录，须以上述当前检查点判断最新状态。

## CoreUtils 源码密码函数与原版 Quarantine 进程对象（前一阶段）

CoreUtils 新的公开描述符、上下文和调用约定依据本地原版 Intel 缓存中的指针、数据及机器码核对：描述符含三个回调和两个长度字段，大小 40 字节；Hash context 为 216 字节，HMAC 外层 pad 从 +216 开始。SHA1/SHA256/SHA512 的导出是指向描述符的指针，摘要/块大小分别为 20/64、32/64、64/128。HKDF 最后三个参数为 info 长度、输出长度、输出指针。ABI 推断、原始数据和来源 SHA 保存在 `artifacts/coreutils-crypto-native-abi.json`，没有使用零描述符或假摘要。

全部 132 个 CoreUtils 源文件重新编译，保留原有 1,429 个导出，新增 digest-size 查询和三个描述符导出。替换原有九个 CryptoHash/CryptoHMAC/CryptoHKDF 占位函数，以实际 CommonCrypto 摘要回调实现流式/单次 Hash、HMAC 和 HKDF；并不代表其余 AES、AEAD、随机数或其他 CoreUtils 占位接口已经实现。HKDF 支持三个内建摘要及 RFC 的 255 个摘要块上限。独立 Linux Python hashlib/hmac 参考与实际 Darling 运行结果比较，48 个 Hash、480 个 HMAC、324 个 HKDF 样例共 852 组，通过单次/分段计算、上下文保护字和输出边界检查。HKDF 测试含零长度输出及最大扩展长度。旧 CoreUtils 对照仍报告缺少 SHA512 描述符。

Quarantine 重新编译原有两个源文件，保留全部 28 个原有导出，明确重导出原版库中已有的 22 个内部进程对象 API。对象分配、初始化、标志范围、标识、最多 64 字节元数据和设置了有效路径模式的独立克隆共 797 项检查通过。原版对象代码未改，MAC 策略调用仍得到实际 ENOTSUP；未将旧的 dummy qtn_proc 对象别名到新 API。原版缓存恢复只将两个 typed malloc 导入指向已验证的 Apple 原样分配器回退层，原有策略调用没有覆盖。启动所需的小型 helper 放在私有客体根目录，避免引入依赖 CoreFoundation 的大兼容组件。

有两个明确保留的失败。首先，第一次没有设置路径模式的 native clone 在 strdup(NULL)/strlen 处失败；其二进制、源码、日志和 core 栈诊断单独保存。有效模式的测试通过，不证明这个 NULL 模式分支兼容。其次，真实 cfprefsd 已能加载，但其入口要求以 flags 6 应用 Quarantine，Darling 后端当前返回 ENOTSUP，因此守护进程按原版逻辑退出。不能仅保存一个内存 token 就声称策略已生效；还需实现真实文件传播、执行检查和状态生命周期。已从本地 BootKernelExtensions.kc 定位原版 x86_64 Quarantine 组件、238 个定义符号及 syscall/create/exec 实现，作为下一步行为依据；没有加载任何内核模块。

严格 UTI 预检仍未通过。明确跳过 UTI 的诊断实际运行原版工程命令，现场 gdb 捕获到原版 Xcode、libxcodebuildLoader 和 DVTFoundation 的映射及调用栈，停在 CoreFoundation 等待系统 cfprefsd 回复。新探针另以 /proc 观察真正的 Xcode 进程，将“已启动”和“已返回”分开记录；30 秒诊断确认已启动但未返回，超时由观察期限终止，不能记成 Xcode 自行报错。此前仅用返回标记判断启动的旧报告不足以识别这种挂起。

新客体根目录下，既有进程身份 106 项、Sandbox 95 项、跨动态库异常 3,215 项、分配器 251 项、替换函数 331 项检查均通过。此前 chained-fixup 替换函数、Security NSXPC、真实签名及完整 Unity/CocoaPods 流程的限制继续保留。原版 Xcode SHA、工程和命令参数未改；默认入口未切换。

复现入口（实际 Darling 会话串行执行，避免等待锁消耗外层 timeout）：

```bash
python3 scripts/build-coreutils-crypto-source.py
python3 scripts/rebuild-c-cache-image.py --target quarantine-proc-native --lazy-functions --analyze-code
python3 scripts/stage-crypto-quarantine-runtime.py
python3 scripts/test-coreutils-crypto-source.py
python3 scripts/test-quarantine-proc-native.py
python3 scripts/test-crypto-quarantine-regression.py
python3 scripts/probe-xcode-service-runtime.py --crypto-quarantine --cfprefsd-daemon --mdns-library-only version  # 当前预检超时
python3 scripts/probe-xcode-service-runtime.py --crypto-quarantine --cfprefsd-daemon --skip-uti-diagnostic --timeout-seconds 30 build  # 诊断仍等待真实偏好设置服务
python3 scripts/record-coreutils-quarantine-progress.py
```

CoreUtils 源码补丁为 `artifacts/darling-coreutils-crypto-source.patch`，反向应用检查通过。前一阶段 119 个证据/脚本/状态文件按内容 SHA 归档到 `artifacts/expected-sandbox-runtime-history/manifest.json`。当前代码与运行证据由新检查点校验；阶段通过不代表完整 Xcode 流程完成。

## libc++ 异常、Sandbox 后端与进程身份（此前检查点）

libc++ 新类沿用 LLVM 21.1.8 的异常文本和基类 ABI，以兼容声明适配 Darling 旧构建头文件。现有十个包装对象加新源文件重链接，保留 103 个直接导出并新增四个；**完整 libc++ 没有重编**。使用原版 SDK 的 C++23 消费者，实际验证跨动态库的 typed/base/std::exception catch、RTTI/vtable 归属、exception_ptr copy/rethrow 和 payload 析构。原有分配器 251 项、替换 new/delete 331 项、11,427 个有限浮点格式化样例及 15 个 long double 窄化样例在新运行环境回归通过。

上述分配器回归保持原测试的 macOS 11 链接目标。另一次 macOS 15.4 目标的现代 chained-fixup 程序没有正确采用自定义 new/delete，失败二进制和日志完整保存在 `artifacts/pid-generation-cpp-chained-replacements-failure.json`；这条加载器兼容路径仍未实现，不能用通过的旧格式测试替代。

Sandbox 后端读取真实进程注册表及其未受限状态，验证 PID、audit PID version、保留槽、参数指针与 filter；失效身份报 ESRCH，不支持的 POSIX 检查和配置应用报 ENOTSUP。fork 继承未受限状态。没有配置引擎、扩展令牌或交互审批实现；`sandbox_init*` 也不再声称已应用一个并不存在的配置。测试没有链接测试捕获后端。

同时修正 Darling 的进程身份路径：注册表的生命周期 ID 与 fork/exec 的 PID version 分开保存；成功 exec 重建 Mach task 后分配新版本，失败 exec 保留旧版本。追加只读 RPC，使 `proc_pidinfo` 和 Mach audit token 使用同一个编号，并将成功返回值从 1 修正为实际结构体长度。全部 875 个 libsystem_kernel 源文件重新编译；原有六个配套客体组件逐一校验。旧编译输入按原 SHA 冻结，旧构建报告和基线服务端产物保留，未放宽源文件校验。

严格集成仍未通过。实际现场栈显示：lsd 卡在 `_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_CFPREFSD`，UTI 客户端卡在等待 lsd 的同步 NSXPC 回复；延长观察期限未证明通信恢复。已接入原版 cfprefsd daemon；其真实加载失败为缺少 Quarantine 内部接口 `__qtn_proc_alloc`，因此预检仍超时。没有将现有 placeholder qtn_proc 对象别名成新接口。另一次明确省略 UTI 预检的工程诊断已越过 libc++ RTTI，实际启动原版 Xcode，退出 255 并报告 `_AMDeviceCreateWithRemoteDeviceWithError`。该符号存在于 Xcode 随附的 MobileDevice 包。追加真实框架搜索路径后，未修改的原版 MobileDevice 已被加载，Xcode 当前转而报告 CoreUtils 缺少 `_kCryptoHashDescriptor_SHA512`，仍退出 255。诊断执行不代表严格预检或构建成功。

复现入口（Darling 会话必须串行；前置阶段产物保持原 SHA）：

```bash
python3 scripts/build-sandbox-check-source.py
python3 scripts/build-expected-access-source.py
python3 scripts/build-sandbox-policy-source.py
python3 scripts/build-libsystem-kernel-source.py --output-dir runtime/pid-generation-kernel-source --variant-base runtime/sandbox-check-source/darling-root --report artifacts/pid-generation-kernel-source-build.json
python3 scripts/stage-pid-generation-source.py
python3 scripts/test-process-generation-source.py
python3 scripts/test-sandbox-policy-source.py --pid-generation
python3 scripts/test-pid-generation-cpp-regression.py
python3 scripts/probe-xcode-service-runtime.py --pid-generation --cfprefsd-daemon --mdns-library-only version
python3 scripts/probe-xcode-service-runtime.py --mobile-device --cfprefsd-daemon --skip-uti-diagnostic build
python3 scripts/record-expected-sandbox-runtime-progress.py
```

源码补丁为 `artifacts/darling-libcxx-expected-source.patch`、`artifacts/darling-sandbox-policy-server-source.patch`、`artifacts/darling-pid-generation-kernel-source.patch`、`artifacts/darling-sandbox-query-policy-source.patch`；包含各组件相对上游的累积修改，反向应用检查通过。前一 Sandbox 阶段证据按内容 SHA 归档于 `artifacts/sandbox-check-history/manifest.json`。正式加载路径没有使用测试捕获 hook。

## Sandbox 源码查询与尚缺的服务端策略（此前检查点）

检查首先确认，当前查询函数原先来自 Darling `libsystem_sandbox` 的占位实现，直接返回 0；`SANDBOX_CHECK_NO_REPORT` 的值原先也是 0，`SANDBOX_CHECK_ALLOW_APPROVAL` 没有导出。现已在 Darling 源码 `src/sandbox/check.c` 实现 PID 和 by-value audit token 两个变参查询入口，沿原有 `__mac_syscall` RPC 路径调用 `Sandbox` operation 2，保留真实错误。七个 uint32 标志与原版一致，其中 NO_REPORT 为 `0x40000000`、ALLOW_APPROVAL 为 `0x08000000`。没有新增正式运行时的逐函数 hook，也没有把缺少策略的错误转换成允许。

用户态 ABI 覆盖全部 20 个原版 filter 编码、六位标志组合、两个身份入口、标量/双参数编码、PID 符号扩展、audit PID/version、保留字段、旧操作名转换、结果布尔化和错误返回。测试专用捕获库通过进程内 interpose 检查原版与源码实际传入的 20 个 MAC 参数槽，并提供已知允许/拒绝/错误结果；12,814 个样例、281,689 项检查通过。该捕获库只链接到这个测试程序。另一个不链接捕获库的实际查询程序，完成 2,560 个样例、5,141 项检查，源码与原版都返回真实 ENOPOLICY。测试后端不是 Sandbox 审批、权限执行或隔离实现。

完整三文件源码库保留原有 49 个导出，新增六个标志导出；既有 NO_REPORT 的值修正。通过配套的七组件私有目录选择该库，其余六个组件的二进制 SHA 保持不变。系统 libSystem 原有的整库重导出已经能看到这些新增符号，无需追加常量兼容库。

严格回归暴露了真实集成缺口：前四种 UTI 的标识、首选扩展名和 URL 扩展都正常，但 `conforms(to: .data)` 在 Swift 预检第 27 行失败。构建、版本和 SDK 三个脚本均因此退出 1，**没有启动 Xcode**，不能记成 Xcode 自身返回 1。新日志记录了 lsd 的 `file-read-data` 查询：NO_REPORT/CANONICAL 标志、audit 身份，实际返回 ENOPOLICY 103。服务端当前只有 Quarantine MAC 处理，没有 Sandbox。重新选用上一阶段运行库后，严格 UTI 和原版版本查询仍通过，确认回归与这个 Sandbox 组件变化有关；导致类型归属失败的具体 LaunchServices 分支还需继续追踪。

单独诊断显式打印 `SERVICE_RUNTIME_UTI_PREFLIGHT_SKIPPED_DIAGNOSTIC_ONLY`，省略会终止会话的 UTI 程序，再执行参数不变的原版工程命令。该次实际退出 255，缺少 `__ZTINSt3__119bad_expected_accessIvEE`，不再报告 Sandbox 标志缺失。这次诊断不属于通过预检的集成结果，没有构建成功。旧 NSXPC、通知及签名/信任问题也没有据此视为解决。

下一步需要在 darlingserver 补真实的 Sandbox 查询状态和进程身份处理，区分实际未受限进程、无法实施的隔离、POSIX 与审批请求；不能使用统一返回允许来恢复预检。现有 `sandbox_init` 等其他占位实现仍在，不能宣称已应用策略。另一独立缺口是原版 DiskImages2 需要的 libc++ `bad_expected_access<void>` 实现/RTTI。

复现入口（已有前置恢复库和运行库时；Darling 会话串行）：

```bash
python3 scripts/build-sandbox-check-source.py
python3 scripts/test-sandbox-check-source.py
python3 scripts/probe-xcode-service-runtime.py --sandbox-checks --trace-sandbox build  # 当前预检退出 1，Xcode 未启动
python3 scripts/probe-xcode-service-runtime.py --sandbox-checks --trace-sandbox --mdns-library-only version
python3 scripts/probe-xcode-service-runtime.py --sandbox-checks --trace-sandbox --mdns-library-only showsdks
# 仅诊断后续加载缺口，明确不执行 UTI 预检：
python3 scripts/probe-xcode-service-runtime.py --sandbox-checks --trace-sandbox --skip-uti-diagnostic build  # 当前 255
# 上一运行库的严格对照，仍应为 0：
python3 scripts/probe-xcode-service-runtime.py --typed-new-delete --mdns-library-only version
python3 scripts/record-sandbox-check-progress.py
```

源码补丁为 `artifacts/darling-sandbox-check-source.patch`。前阶段证据已按内容 SHA 归档于 `artifacts/security-current-item-history/manifest.json`。新源码、二进制、样例、真实集成失败及直接诊断结果的 SHA 均在当前检查点中；Xcode 二进制、原工程参数和默认启动入口保持原样。

## 现代 Security 回复 ABI、源码分配接口及弱符号绑定（此前检查点）

`SecItemFetchCurrentItemDataAcrossAllDevices` 函数体、`SecItemCurrentItemData` 类声明与实现均来自固定 Apple 开源提交，保持原样。结果类与原版缓存布局一致：大小 24 字节，持久引用及可空修改时间字段分别位于 8/16。接口通过真实客户端获取 NSData、NSDate、NSError 三个回复值，错误解码类索引改为 2。测试覆盖成功、无结果、错误、附带部分数据的错误、无修改时间、对象跨池存活及 strong 属性不复制数据的行为。

Darling 源码中的旧 CF API 继续返回持久引用与错误两个公开值，其内部块签名同步接受现代第三值。独立组件将这段真实旧 API 源码编译为测试别名，避免替换原版 Security 的既有导出；原版旧端点和旧 API 保持原有组合。源码中的旧服务器适配保留现有权限检查和错误，将它不提供的可空修改时间设为 nil。完整 Security/服务器没有重编和执行，因此不代表真实云服务已支持。

Darling libc++ 的 `typed_new_delete.cpp` 实现四个新运算符，委托现有标量/数组 new/delete，保留实际零尺寸、对齐、new_handler、bad_alloc 与替换函数行为，不提供类型分区隔离。现有 libc++ 包装库使用九个原有对象重链接，再加入该源文件；重链接基线除输出相关 UUID 外与原库逐字节相同，保留原有 99 个直接导出。完整 libc++ 没有重编。

测试发现 LLVM 链接输出中的弱绑定符号未排序，与旧 dyld 的有序合并遍历不匹配，导致应用自定义数组分配/释放函数未被调用。`normalize-macho-weak-bind.py` 仅规范化这张表：九个符号及其 flags、type、segment、offset、addend 全部相同；指令不变，后续 LINKEDIT 载荷整体平移 32 字节、内容逐字节保留，并同步调整元数据偏移。未排序控制库的替换函数调用次数为 `80/0/40/0`，修正后的同一测试为 `40/40/40/40`。分配/异常 251 项、替换函数 331 项检查通过。现有格式化测试保留所有数值、保护字节和往返断言，仅通过编译参数指定这次应使用的确切库路径；11,427 个有限浮点样例、15 个原版 long double 窄化样例与独立 Linux 参考比较通过。

原版工程已越过 Security 接口和 CoreStorage 的 typed delete 缺失。目前由 DiskImages2 报告缺少 `_SANDBOX_CHECK_ALLOW_APPROVAL`；原版 uint32 值已核对为 `0x08000000`，尚未加入。下一步还需查清实际 sandbox_check 提供方及其处理该标志的行为；补常量不能代表策略审批已实现。ProtectedCloudStorage 的 72 个 Security 导入目前都有对应导出，此静态结果不证明完整加载或云功能可用。四个生产 Security 客户端回调仍超时，匿名 NSXPC 测试仍返回 4099，两个失败均保留。

主要复现入口（依赖此前恢复的库和对象，Darling 会话串行执行）：

```bash
python3 scripts/build-security-cloud-rpc.py
python3 scripts/stage-security-cloud-rpc.py
python3 scripts/build-typed-new-delete.py
python3 scripts/test-typed-new-delete.py  # 两个负例应失败，脚本整体应为 0
python3 scripts/test-typed-new-delete-to-chars.py
python3 scripts/test-security-cloud-rpc.py --typed-new-delete  # 当前整体 1，保留传输失败
python3 scripts/probe-xcode-service-runtime.py --typed-new-delete build  # 当前 255
python3 scripts/probe-xcode-service-runtime.py --typed-new-delete --mdns-library-only version
python3 scripts/probe-xcode-service-runtime.py --typed-new-delete --mdns-library-only showsdks
python3 scripts/record-security-current-item-progress.py
```

源码补丁为 `artifacts/darling-security-current-item-source.patch` 和 `artifacts/darling-libcxx-typed-new-delete-source.patch`。前一阶段证据已按内容 SHA 归档到 `artifacts/security-cloud-rpc-history/manifest.json`，当前运行和源码检查由新检查点记录。Xcode 二进制和原工程参数未改；基础版本/SDK 回归未启用可选随附包挂载，不能代表扩展组合已构建成功。

## 源码 Security RPC 客户端与尚未通过的真实传输（此前检查点）

已将 Apple Security 提交 `db15acbe6a7f257a859ad9a3bb86097bfe0679d9` 的三个函数体原样移入 Darling 源码：`SecItemUnsetCurrentItemsAcrossAllDevices`、`SecItemFetchCurrentItemOutOfBand`、`SecItemFetchPCSIdentityOutOfBand`。旧客户端协议新增对应声明；原版查询/结果类与 NSError 的允许解码类配置同步补齐，不依赖启用 Octagon 后端。CMake 源文件列表与导出列表也已更新，但完整 Security.framework 尚未重编。

实验运行库直接编译整个更新后的 `client_endpoint.m` 与三个客户端函数。独立组件对客户端类、协议和内部 helper 使用命名空间，避免与原版 Security 的旧客户端重名；不修改旧类的方法。组件仍读取原版导出的真实 `gSecurityd`，其 81 个函数指针之后的 `secd_xpc_server` 偏移 0x288 已和原版机器码核对；未定义替代全局变量。与原版 Security 的命名重导出保留既有指令和导出载荷。

协议/类配置、三个 Security 重导出与原函数地址相同、全局地址归属等 14 项检查通过。本地测试通过真实客户端函数和原版全局入口，将已知测试数据及刻意构造的测试错误传入/传出，共 45 项检查通过。此测试后端仅用于验证前端转发，不能代表钥匙串、权限检查或云服务。

两项实际传输检查没有通过：三个生产 API 的错误回调在等待期限内没有到达；使用匿名 NSXPC listener 的协议往返返回真实 `NSCocoaErrorDomain` 4099。它们没有被改成成功，也没有提前从客户端返回伪造错误来规避传输。当前还不能据此确定服务是否存在及具体故障层。源码中发现 libxpc 的激活错误路径没有完成激活/投递事件，是待验证的候选原因。

原版工程不再报告此前三个缺失导出，当前加载器停在 `SecItemFetchCurrentItemDataAcrossAllDevices`，尚未开始编译。该函数还需要新结果类型及包含三个参数的现代回复协议；旧声明只有两个回复参数，不能只加符号。基础 `-version`、`-showsdks` 回归未启用两个可选随附包挂载，因此不代表接入全部随附组件的环境已工作。

复现入口（依赖此前 mdns 与源码运行库，实际 Darling 会话串行执行）：

```bash
python3 scripts/build-security-cloud-rpc.py
python3 scripts/stage-security-cloud-rpc.py
python3 scripts/test-security-cloud-rpc.py  # 当前整体返回 1，保留两项传输失败
python3 scripts/probe-xcode-service-runtime.py --security-cloud-rpc build  # 当前 255
python3 scripts/probe-xcode-service-runtime.py --security-cloud-rpc --mdns-library-only version
python3 scripts/probe-xcode-service-runtime.py --security-cloud-rpc --mdns-library-only showsdks
python3 scripts/record-security-cloud-rpc-progress.py
```

源码补丁为 `artifacts/darling-security-cloud-rpc-source.patch`；编译、暂存、测试和原版工程证据均由当前检查点记录 SHA。Xcode 二进制和项目参数保持原样，默认 CI 入口未切换。

## 原版随附组件依赖与源码 XPC/Security 值类（此前检查点）

12 个原版库包括 libmdns、PacketFilter、RemoteXPC、RemoteServiceDiscovery、StorageKit、AppServerSupport 及磁盘/存储依赖。恢复过程中修复了 RemoteXPC 的 DATA/CTF 共页映射：保留原始地址、权限和全部 824 字节 CTF 数据，未禁用加载器检查。单独按 `__CTF` 段名查找的 DTrace 工具兼容性仍未验证。StorageKit 和 DiskImages2 的 Swift 元数据已结构性修复，实际磁盘/密码操作未验证。

Darling libxpc 源码新增 `xpc_array_create_empty`，完整重编 39 个源文件、640 个导出，并组合为配套的七组件私有运行目录。旧运行库缺符号的反例与新实现的 1,041 项实际数组类型、所有权、增长、修改和遍历检查通过。原版 mdns TLV 代码通过 307 项检查；原版 RemoteXPC/RSD 的 14 个类完成注册和 56 项检查。立即绑定仍因 LoggingSupport 缺少 `__dyld_dlsym_blocked` 失败，`test-mdns-native.py` 因此整体返回 1；这没有被记成完整依赖闭包通过。

四个 Apple 开源 Security 查询/结果类保留原有实现，加入 Darling Security 源码并独立编译，通过命名重导出供原版 Security 使用。102 项检查覆盖原版类尺寸、15 个 ivar 偏移、对象所有权和真实安全归档往返；拒绝未授权自定义类时未执行其解码器。原版 Foundation 对一个声明为 NSString 的字段接受了内联 NSNumber，此现象被保留记录，未声称严格字段类型检查已通过。这四个类只有数据/序列化功能，不等于 securityd 或云钥匙串后端。

原版 XcodeSystemResources 和 MobileDevice 包载荷仅在本次 Darling server 的挂载命名空间中接入；共享框架前缀未发布，只有空的 `Library/Apple` 挂载目标目录保留。未执行安装脚本、加载内核扩展、伪造收据或首次启动完成状态。接入随附组件后的原版工程已越过此前 mdns/XPC/类缺失错误，目前由 ProtectedCloudStorage 报告缺少 Security 客户端 RPC 导出，退出 255。基础 SDK 检查没有接入这两个包，因此只能作为回归检查；该次列举后的 lsd 快照有 PID、LastExitStatus 为 0，不能据此认定长期通知服务已正常。

在已恢复前置缓存库/包载荷后，主要重建与验证入口如下（Darling 会话必须串行）：

```bash
python3 scripts/build-libxpc-source.py --output-dir runtime/xpc-collections-source --report artifacts/xpc-collections-source-build.json --variant-base runtime/runnable-archs-source/darling-root
python3 scripts/stage-xpc-collections-runtime.py
python3 scripts/build-security-out-of-band-values.py
python3 scripts/stage-mdns-native.py
python3 scripts/test-xpc-array-empty.py
python3 scripts/test-mdns-native.py  # 当前返回 1，保留立即绑定失败
python3 scripts/test-security-out-of-band-values.py
python3 scripts/probe-xcode-service-runtime.py --mdns-library-only version
python3 scripts/probe-xcode-service-runtime.py --mdns-library-only showsdks
python3 scripts/probe-xcode-service-runtime.py --mdns build  # 当前返回 255
python3 scripts/record-mdns-source-progress.py
```

12 个缓存重建目标及原始 SHA 位于 `config/cache-image-pins.json`，各自重建命令和修复记录位于 `runtime/rebuilt-*/reconstruction.json`。源码补丁为 `artifacts/darling-xpc-collections-source.patch` 和 `artifacts/darling-security-out-of-band-values-source.patch`；完整证据与边界见该阶段检查点。原版 Xcode 二进制及项目参数未修改。

## libtrace 日志包与 FSEvents 小栈修复（此前检查点）

本阶段先捕获了原版工程构建的实际 SIGSEGV：SystemConfiguration 的 `get_sysctl_val` 错误日志路径写入了 `_os_log_pack_fill` 返回的空指针。Darling 的该接口及 pack size/send 原先是占位实现。现已直接在 libtrace 源码中实现 Intel 日志包头布局、尺寸计算、填充、编译器参数编码，以及复用实际 ASL/hook/fault 回调的发送路径，完整重编九个源文件。原有 142 个导出全部保留，当前共 145 个导出；没有关闭错误日志来规避崩溃。

有效包头的 sizeof 为 72，参数数据从字节 68 开始，saved errno 和参数尺寸分别在字节 64/66。测试直接执行原版 Intel 库的 size/fill 叶函数，对八种有效尺寸逐字节比较，只有两个实际调用点的返回地址按预期不同。269 个检查覆盖布局、保护字节、实际格式化/隐私/中文/errno/浮点/故障回调，并验证三项 API 的函数地址确实属于当前源码库；原有日志 hook 的 1,642 个检查、419 次事件回归也通过。这不证明原版统一日志服务、pack compose 等剩余接口全部支持。

越过该崩溃后，实际 Xcode 进程在 FSEvents `_readEvents` 的 64 KiB 栈缓冲区下撞上了 dispatch worker 的保护页。已经把读取缓冲区改为堆分配，并在异常清理中释放；完整两文件组件重编，保留 29 个原有导出，当前共 57 个导出。真实 65,536 字节线程栈上的公开 start/write/sync-flush 测试收到两个实际文件事件，原有 88 项 flush 检查同时通过。此前复杂 CFRunLoop 定时等待问题没有据此宣称修复。

原版工程目前已能记录并返回正常错误：DVTDownloads 随附框架缺失，退出 70。用户提供 Xcode 中的 `XcodeSystemResources.pkg` 已校验载荷归档 checksum 并解出 1,828 个文件；实验接入其原版 CoreDevice 后，加载器报告还缺 `/usr/lib/libmdns.dylib`，退出 255。已撤回这八项工程前缀链接，原始包和载荷保留待补齐依赖。没有伪造安装收据、首次启动完成状态，随附 postinstall/devicectl 设备镜像更新也没有执行。

另已让原版 `_distnote` 用户/组 241 在一次私有会话的实际 guest overlay 中可解析。必须在 Darling 建立 overlay 之后挂载；在其 upperdir 的底层文件上预先 bind 不会生效。共享账户文件保持原样。补充组列表仍有错误；原版 distnoted 当前因缺少 `_sandbox_check_by_reference` 而中止，不能视为通知协议已运行。原版 SDK 列举退出 0 后 lsd 仍有退出 132 的问题。

当前重建/验证命令如下；前阶段的缓存恢复和运行库仍是依赖，实际 Darling 会话需串行执行：

```bash
python3 scripts/build-libtrace-source.py --output-dir runtime/libtrace-pack-source --report artifacts/libtrace-pack-source-build.json
python3 scripts/build-fsevents-source.py --output-dir runtime/fsevents-heap-source --report artifacts/fsevents-heap-source-build.json
python3 scripts/test-log-pack.py
python3 scripts/test-fsevents-heap.py
python3 scripts/probe-xcode-service-runtime.py --log-pack version
python3 scripts/probe-xcode-service-runtime.py --log-pack showsdks
python3 scripts/probe-xcode-service-runtime.py --log-pack build
python3 scripts/record-log-pack-progress.py
```

build 当前应返回 70。保留的真实调试证据为 `logs/xcode-project-crash.*` 和 `logs/xcode-project-pack-crash.*`，完整源码补丁为 `artifacts/darling-libtrace-pack-source.patch`、`artifacts/darling-fsevents-heap-source.patch`。随附包可用 `scripts/extract-xip.py --member Payload` 解出；`stage-xcode-system-resources.py` 默认只记录暂存载荷，`--publish-prefix`/`--unpublish-prefix` 才显式接入/撤回工程前缀。该实验组合的依赖闭包尚不完整。下一步依据在 `artifacts/log-pack-next-runtime-analysis.json`；完整 Unity/CocoaPods 构建、归档、签名、导出及默认 CI 入口整合均未通过。

## 源码 Objective-C runtime 与原版 SDK 列举（此前检查点）

已在 Darling 的 objc4 源码中添加 `sel_lookUpByName`，使用实际内建 selector 查询和受 selLock 保护的注册表，未知名称不会被注册；完整重编 43 个源文件，保留原有 770 个导出并新增该接口。私有枚举辅助库转发到这个源码实现，旧的 UUID/代码/布局检查仍保留在原先组合中，没有削弱检查。直接及经辅助库调用、并发名称查询、类枚举、NSInvocation 标量/浮点/结构体返回和 tagged pointer 回归通过。

当前组合使用恢复的原版 `libswiftFoundation` 转发库，并把常量浮点辅助符号转发到原版 Foundation 的真实类，消除了重复类定义。原版 Apple clang 生成的常量浮点客户端通过位模式、布局、CF 桥接和容器行为检查。相关源码补丁为 `artifacts/darling-objc-selector-source.patch`。这是分组件源码构建与私有兼容层的组合，尚未统一成完整 Darling 分发版。

原版 `xcodebuild -showsdks` 在同一会话加载原版 lsd/dirhelper 后首次退出 0；实际输出包含 iOS、macOS、tvOS、visionOS、watchOS 和 DriverKit SDK。启动脚本直接执行原版 `xcodebuild "$@"`，没有生成或替换 SDK 输出。版本与 SDK 结果只证明这些命令可执行，不能证明工程构建成功。

尚有明确失败：SDK 查询后 lsd 的 LastExitStatus 为 132，日志显示注册通知无法查找分布式通知服务；原版 XcodeSmoke 工程构建退出 1，未产生成功标记。该次构建的精确退出路径仍在调查。两个日志都出现 quotactl ENOSYS，因此不能仅凭这一行认定它导致构建失败。若干暂存系统框架缺少原版 Info.plist 资源，Xcode 也会打印跳过框架的警告。

已有此前运行库和缓存恢复结果时，按顺序重建和验证：

```bash
python3 scripts/build-objc-source.py --output-dir runtime/objc-selector-source --report artifacts/objc-selector-source-build.json
python3 scripts/stage-objc-selector-source.py
python3 scripts/test-objc-selector-source.py
python3 scripts/rebuild-c-cache-image.py --target swift-foundation-shim-native --lazy-functions
python3 scripts/stage-foundation-coherent.py
python3 scripts/test-foundation-coherent.py
python3 scripts/probe-native-layer-xcode.py --foundation-coherent version
python3 scripts/probe-xcode-managed-services.py showsdks
python3 scripts/probe-xcode-managed-services.py build
```

原版 lsd 的预先回归命令及完整参数记录在 `artifacts/native-lsd-foundation-coherent-probe.json`，该报告必须与当前组合匹配。最后一个 build 命令目前失败。实际 Darling 会话必须串行执行；默认 CI 入口尚未切换。

## FSEvents 源码 flush 与回调生命周期（此前检查点）

本阶段直接修改 Darling FSEvents 的两个实现文件、私有/公共头文件和 CMake。`FSEventStreamFlushAsync` 实际读取非阻塞 inotify FD，返回已经排队的最大真实事件编号，再异步交付；`FSEventStreamFlushSync` 等到调用时已有事件的回调被执行，保持队列/run-loop 的交付上下文。没有用固定返回值或伪造文件事件绕过接口。事件编号目前仍局限于该流，不能视为持久的系统全局 FSEvents 编号。

每个流使用自己的串行状态队列管理 FD 和事件编号。跨队列交付使用独立的不可变路径、flags 和 IDs 批次，回调内再次 flush 不会重新分配正在读取的数组。实现接入创建时指定的 latency 和 NoDefer 计时行为，并处理停止/重启、回调内失效、清理待投递回调和最后一次 release。dispatch source 与 run-loop context 使用弱引用，避免流持有自身；实际 inotify FD 在取消完成后关闭，并设置 CLOEXEC。完整两文件组件重编后保留原有 29 个导出，增加接口及内部类/字段后共 57 个导出。没有完成整个 Darling 分发版重编。

真实测试包含三种回调格式、每种 64 个文件的实际创建/写入、异步水位、同步完成、回调内 async/sync 重入、暂停/同队列/并发队列、四个并发 flusher、真实 latency/NoDefer、run-loop 交付、停止后积累事件再重启、失效与释放时的 context/FD 清理。当前每轮有 88 个显式计数检查，另有逐事件/载荷断言，最终代码再串行重复三轮通过。原版 lsd/UTI 和 Xcode 版本查询在同一组合下通过。

**复杂 timed run-loop 行为仍有未解决异常。** 早期扩展测试曾在原版 CoreFoundation 的 `__CFRunLoopRun` / `__CFRunLoopServiceMachPort` 等待中卡住，即使外部线程已记录 flush 完成。调试日志和真实 GDB 栈保留。最终的跨线程 flush 测试在完成交付后明确调用 CFRunLoopStop 结束服务循环；三次重复通过只证明这个交付协议，不证明原先的定时等待问题已修复。单独的 native CF 超时探针通过，也不能替代原失败场景。递归目录、持久历史/全局编号、相对设备流、全部 flags/扩展 file ID 及完整丢失/重命名语义同样未全部实现或核验。

原版 `xcodebuild -showsdks` 现在退出 1，报告 `Objective-C selector backend UUID/code/layout guard rejected incompatible runtime`。独立进程验证 sel_isMapped 确实由当前源码 libobjc 提供，其 UUID 与旧适配器固定的库不一致；保护检查保持原样。初始化还加载了旧 libswiftFoundation 与常量浮点兼容类，和原版 Foundation 出现重复类。下一步需要统一实际运行库和兼容层，而不是削弱检查。分析见 `artifacts/fsevents-flush-next-runtime-analysis.json`。

当前源码补丁为 `artifacts/darling-fsevents-flush-source.patch`，已对 Darling 源码反向校验。已有此前运行库和缓存恢复结果时，可串行重建验证：

```bash
python3 scripts/build-fsevents-source.py \
  --output-dir runtime/fsevents-flush-source \
  --report artifacts/fsevents-flush-source-build.json
python3 scripts/test-fsevents-flush.py
python3 scripts/repeat-fsevents-flush.py
python3 scripts/probe-objc-selected-owner.py
python3 scripts/probe-native-layer-xcode.py --fsevents-flush version
python3 scripts/probe-native-layer-xcode.py --fsevents-flush showsdks
```

最后一个命令当前应退出 1，不能视为 SDK 列举成功。原版服务的完整回归参数在 `artifacts/native-lsd-fsevents-flush-probe.json`；回归后执行 `python3 scripts/record-fsevents-flush-progress.py` 发布当前检查点。所有实际 Darling 会话串行执行，默认入口尚未切换；完整工程编译、归档、签名及导出仍待验证。

## 原版 Combine 与 FSEvents 源码事件修复（此前检查点）

当前私有组合选用恢复的完整原版 Intel Combine，替代该组合中早期的 OpenCombine 兼容实现：2,023 个导出、4,362 个函数、180 个跳转表，恢复了 390 个 Swift context、255 个泛型 context、725 个 conformance 及四个 ObjC 可见 Swift 类。没有 backend-call override、导入重定向或替代 Publisher。结构恢复本身不证明 Swift ABI 可运行；运行验证另行执行。

实际测试直接使用未改动的 Apple SDK Combine 接口编译客户端，确认 `Just.setFailureType` 的函数地址属于原版库。测试通过十种整数/Unicode 字符串/持有字符串结构体的泛型 Result.Publisher、引用载荷销毁、map/catch/Future、背压与取消；还通过 64 个 XCSourceControl 风格的 tryMap/flatMap/erase/store 成功与失败链，以及 Published/ObservableObject 的反射、通知和取消。DVTFoundation 的 40 个、XCSourceControl 的 25 个 Combine 导入均存在；静态导出检查不代表这两个原版消费者已完整执行。其他运算符、调度器和并发使用仍未全部核验。

越过 Combine 后，原版 SDK 列举缺少 `FSEventStreamFlushAsync`。检查真实 Darling FSEvents 后端发现，它每次读取 inotify 数据后只处理第一条记录，丢弃同一缓冲区中的其他记录。已经直接修改 `FSEventsImpl.m`，遍历完整的变长记录并处理 EOF；完整两文件组件已重编，原有 29 个导出全部保留。同一个真实文件监控客户端连续创建并写入 64 个文件，当前旧库对照只收到 30 个路径/30 个事件 ID，源码修复版收到全部 64 个路径/128 个事件 ID。首次旧库实验收到 31 个路径，原始日志另行保留；丢失数量受调度影响。

**本阶段没有添加假的 FlushAsync 导出，也尚未实现真正 flush。** 原后端忽略创建时的 latency，跨队列共享可变回调数组，缺少递归目录覆盖和持久/全局事件 ID，取消、溢出和相对设备流等语义也未补齐。异步 flush 需要先安全冻结回调批次、实际读取待交付事件并保持队列/run-loop 顺序，否则可能在回调期间重新分配其缓冲区。当前缺口与下一步设计在 `artifacts/fsevents-source-next-analysis.json`。

最终源码 FSEvents + 原版 Combine 组合下，原版 lsd/UTI 和未改动的 Xcode 版本查询通过，SDK 列举仍因上述 flush 缺失退出 255。源码补丁 `artifacts/darling-fsevents-read-records-source.patch` 已对 Darling 仓库反向校验。已有前阶段运行库和原版缓存恢复工具时，可串行重建：

```bash
python3 scripts/rebuild-c-cache-image.py --target combine-native \
  --lazy-functions --experimental-swift --repair-swift-relative --analyze-code
python3 scripts/stage-combine-native.py
python3 scripts/test-combine-native.py
python3 scripts/build-fsevents-source.py
python3 scripts/probe-fsevents-baseline.py --source-fsevents
python3 scripts/probe-native-layer-xcode.py --source-fsevents version
python3 scripts/probe-native-layer-xcode.py --source-fsevents showsdks
```

`python3 scripts/probe-fsevents-baseline.py` 使用未修复的旧 FSEvents，当前应报告实际事件丢失并退出 1；源码版应完整交付并退出 0。SDK 列举目前退出 255。原版服务的完整回归参数见 `artifacts/native-lsd-fsevents-source-probe.json`，回归后执行 `python3 scripts/record-combine-fsevents-progress.py` 发布当前检查点。默认运行库选择未改动，所有 Darling 会话串行执行；这仍不是完成工程构建和签名的交付版本。

## 原版 ImageIO 与源码常量 ABI（此前检查点）

已恢复原版 Intel ImageIO 的 6,522 个导出、9,814 个函数及 201 个跳转表记录，同时恢复 AppleJPEG、ColorSync、IOSurfaceAccelerator、libate，以及 PNG/TIFF/GIF/JP2/JPEG/Radiance 六个资源库，共 11 个原版镜像。代码未用返回空字典的替代实现覆盖。带类型标签的 C++ 分配导入明确转到现有标准 new/delete 后端；最终组合的 scalar/array 两条路径各完成 448 次分配/释放，并通过真实 `bad_alloc` 传播，但没有类型标签隔离。

Darling CoreGraphics 源码增加了 34 个原版值的 CFString 指针变量；Darling libm 源码增加 `matrix_identity_float3x3`，保持三列 16 字节对齐、总长 48 字节及原版填充字节。新文件均加入对应 CMake 列表。本阶段独立编译这些新增组件，通过明确的命名重导出接入现有库，没有声称完成整个 CoreGraphics/libm 重编。原版 ImageIO 唯一缺少的 Darling 旧导出 `kCGImageDestinationDPI` 从原有源码拆到常量文件，保留原有字符串值以满足旧 AppKit；没有实现该旧选项到原版图片目标属性的转换。

实际执行已验证全部 34 个 CFString 的类型/值和 SIMD 矩阵字节/对齐。原版图片源通过真实 PNG、GIF、TIFF 的 CFData 与文件 URL 两条路径，共 6 个场景，返回正确类型、图片数量和文件级 FileSize；GIF 同时返回原版画布、帧和循环元数据。测试文件由 Python 标准库生成并记录摘要。GIF 文件编码的重复次数为 3，当前原版返回 LoopCount 为 4，结果按实际原版行为记录。

**逐图属性和实际像素解码还未通过。** PNG 的逐图属性路径在 `CGImageProviderCreate` 缺失时失败，并经过旧 Onyx2D 的未实现 `O2ColorSpaceCreateWithName` 路径。文件级属性成功不能证明图像提供者、颜色空间、缩略图、JPEG、图像目标或完整 metadata 后端已工作。完整失败日志保存在 `artifacts/imageio-native-properties-probe.json`。

最终组合的原版 lsd/UTI 回归和未改动的 `xcodebuild -version` 通过。`-showsdks` 的实际下一处加载错误是 Combine 的 `_$s7Combine4JustV14setFailureType2tos6ResultOAAE9PublisherVyxqd___Gqd__m_ts5ErrorRd__lF`。当前源码补丁为 `artifacts/darling-imageio-cg-source.patch` 和 `artifacts/darling-imageio-matrix-source.patch`，已对各自仓库反向校验；CG 补丁包含此前已依赖的源码辅助组件。

已有本项目 SDK、缓存恢复结果和上一阶段运行库时，可依次执行：

```bash
python3 scripts/rebuild-imageio-native.py
python3 scripts/stage-imageio-native.py
python3 scripts/analyze-imageio-cg-constants.py
python3 scripts/stage-imageio-cg-constants.py
python3 scripts/stage-simd-matrix.py
python3 scripts/stage-imageio-legacy-key.py
python3 scripts/make-imageio-fixtures.py
python3 scripts/probe-imageio-native.py global
python3 scripts/test-imageio-allocators.py
python3 scripts/probe-native-layer-xcode.py --native-imageio version
python3 scripts/probe-native-layer-xcode.py --native-imageio showsdks
```

最后一个命令目前退出 255。`python3 scripts/probe-imageio-native.py properties` 可重现逐图属性失败。完整原版 lsd 启动参数见 `artifacts/native-lsd-imageio-native-probe.json`；服务回归后执行 `python3 scripts/record-imageio-progress.py` 发布当前检查点。所有实际 Darling 会话串行运行，默认环境和宿主服务保持原来的选择；全量工程构建、归档、签名和导出仍待实现。

## MobileGestalt 与源码 dyld 架构枚举（此前检查点）

本阶段同时保留两个明确区分的实现。Darling 的单文件 MobileGestalt 源码组件实现了产品版本及可读版本属性，读取真实 CoreFoundation system/supplemental 元数据，包括 `ProductVersionExtra` 和 MZ 条件下的 iOS support version。它与原版 Intel 回调进行了 264 个场景、1,868 项断言的差分，并验证实际 guest 元数据。原版 typed getter 返回 autorelease 对象，虽然其 C 名字包含 `copy`。这个源码版本只覆盖所检查的版本属性，没有实现整套设备 API。

当前较完整的 Xcode 实验选用恢复的原版 Intel MobileGestalt，包含原始 `MGIOKitHelper`、`OS_MobileGestalt` 类和真实设备上下文，同时恢复原版 IOMobileFramebuffer/liboah 依赖。MG 没有 backend-call override。两个依赖中的 C++ typed new/delete 接到现有标准分配后端，448 次真实分配/释放与 `bad_alloc` 传播通过；类型标签隔离不支持。硬件信息仍不完整：productType 返回 nil，设备名称查询会使探针退出 1，原因尚未定位；返回过的标识字符串也不代表已审计真实硬件身份。

`macho_for_each_runnable_arch_name` 已实际加入 Darling dyld 的 CMake 源码列表，并将完整 libdyld 从 28 个文件重编为 29 个文件，保留原有 180 个导出。实现摘自固定提交的 [Apple dyld utils.cpp](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld/utils.cpp)，原实现文本保留在 `vendor/apple-dyld-runnable`。接口依据真实缓存文件及 `.development` 是否存在枚举架构，保持停止回调和顺序；当前没有 Cryptex 缓存的 guest 按原版规则回退为 x86_64。它不提供 ARM/Rosetta 执行能力，也不等同于 CPU 指令分级。libSystem 只给这个接口增加命名重导出，实际函数由源码 libdyld 提供，不是安装原版机器码或函数 hook。

源码枚举与原版 182 字节枚举函数、147 字节文件检查函数通过 788 个差分场景，覆盖文件、目录、符号链接、development 缓存、停止顺序和并发。原版指令只作为测试 oracle，未安装进运行环境。完整源码 libdyld 同时通过原有八线程 512 次加载/查询/卸载生命周期、57 镜像快照和原版线程局部存储回归。原版 MG 的架构数组与实际 dyld 回调结果一致，当前组合的原版 lsd/UTI 与 Xcode 版本查询通过。

源码补丁分别在 `artifacts/darling-mobilegestalt-source.patch` 和 `artifacts/darling-runnable-archs-source.patch`，已对对应源码仓库反向校验。后者包含此前需要的 dlopen header 修复。已有本项目 SDK、缓存恢复结果和底层运行库时，可串行重建验证：

```bash
python3 scripts/build-mobilegestalt-source.py
python3 scripts/test-mobilegestalt-source.py
python3 scripts/rebuild-c-cache-image.py --target mobilegestalt-native --lazy-functions --analyze-code
python3 scripts/rebuild-c-cache-image.py --target iomobileframebuffer-native --lazy-functions --analyze-code
python3 scripts/rebuild-c-cache-image.py --target oah-native --lazy-functions --analyze-code
python3 scripts/stage-mobilegestalt-native.py
python3 scripts/build-libdyld-source.py \
  --output-dir runtime/runnable-archs-source \
  --variant-base runtime/mount-path-kernel-source/darling-root \
  --report artifacts/runnable-archs-source-build.json
python3 scripts/stage-runnable-archs.py
python3 scripts/test-runnable-archs.py
python3 scripts/verify-runnable-archs-runtime.py
python3 scripts/probe-mobilegestalt-native.py --source-dyld architecture
python3 scripts/probe-native-layer-xcode.py --runnable-archs version
python3 scripts/probe-native-layer-xcode.py --runnable-archs showsdks
```

最后一个命令目前应退出 255 并报告真实 ImageIO 缺失接口，不能视为 SDK 列举成功。完整 lsd 启动参数记录在 `artifacts/native-lsd-runnable-archs-probe.json`；重新核验该服务及两个 Xcode 命令后运行 `python3 scripts/record-mobilegestalt-progress.py` 发布检查点。所有 Darling 会话由同一个项目锁串行执行。环境仍混合源码组件、恢复的原版库和既有兼容桥接，没有完成全树统一 Darling 构建；此前元数据、容器权限、签名信任及窗口/GPU 限制保留。

## 源码日志回调与 persona 常量（此前检查点）

Darling libtrace 的完整源码组件已扩展为九个文件，新增 `log_hooks.m`，并将 pthread、unwind 加入实际 CMake 依赖。回调从真实 `_os_log_impl` 事件投递：复制和替换 Block、保留旧回调供调用方串联、记录历史最详细级别、抑制同线程递归，并提供实际 fault 信息。`os_log_get_type` 和 fault callback 的旧断言路径已替换。消息字段对照 [WebKit 的 OSLogSPI 声明](https://github.com/WebKit/WebKit/blob/main/Source/WTF/wtf/spi/cocoa/OSLogSPI.h) 及原版 Intel 注册/投递代码核对；原始声明保存在 `vendor/webkit-oslog-reference`。

编译器生成的字符串和对象指针先转换成原版格式化函数能读取的序列化数据池；宽字符串转换成 UTF-8，零精度不会读取源指针，`%m` 保存实际调用时的 errno。公共数据真实复制，私有池按当前源码隐私策略保持缺失。测试通过 1,642 项断言和 419 次观察事件，其中 400 次来自并发线程，覆盖公共 `os_log_error`/`os_log_fault` 宏、原版格式化文本、Block 生命周期、替换、递归和 fault 记录。256 种消息类型字节与原版 getter 一致，原有 21 个 ASL 编码场景及实际输出仍通过。断言数不等于独立场景数。

首次实现无条件创建回调 TLS/锁，导致原版 lsd 在早期初始化时以 132 退出；同运行库下保留的八文件 libtrace 对照通过。现已将观察者专用初始化推迟到实际注册之后，并保存/恢复日志调用者的 errno，最新正常启动的原版 lsd 和完整当前 UTI 测试恢复通过。失败日志和对照证据保存在检查点中；更底层的 Foundation/pthread 早期交互尚未完全定位，不将调试门下的成功视为正常启动成功。

`CONTAINER_PERSONA_PRIMARY`、`CONTAINER_PERSONA_CURRENT` 是导出的 C 字符串指针变量，值从固定原版 Intel 镜像读取。已逐字节比较，并调用原版容器查询 setter 验证真实复制后的字符串；没有伪造 persona 记录或远程查询成功。字符串存储地址与原版不同。该历史检查点的 SDK 列举停在 MobileGestalt 的可读产品版本属性；原版对应函数返回 autorelease 的 Objective-C 对象，不能只按 C 符号中的 `copy` 推断所有权。

最新源码补丁为 `artifacts/darling-log-hooks-source.patch`，包含此前解码修复及新增回调模块，已对 libtrace 子仓库反向校验。已有本项目 SDK、原版库恢复结果和底层运行库时，可按顺序重建、核验：

```bash
python3 scripts/build-libtrace-source.py \
  --output-dir runtime/libtrace-hooks-source \
  --report artifacts/libtrace-hooks-source-build.json
python3 scripts/stage-log-hooks.py
python3 scripts/stage-container-persona.py
python3 scripts/analyze-log-hook-contracts.py
python3 scripts/verify-log-hooks-progress.py
python3 scripts/record-log-hooks-progress.py
```

核验脚本串行运行 Darling，记录真实 SDK 加载错误；退出 255 不代表构建成功。`scripts/probe-native-layer-xcode.py --container-persona showsdks` 可单独重现当前错误。默认启动器未切换，仍未完成 Darling 全量统一构建。回调记录的其他不透明 trace 元数据、stackshot、完整格式插件及持久 logd 服务尚未实现或核验，之前的文件系统、容器策略和窗口/GPU 限制仍在。

## 原版图层与日志接口（此前检查点）

本轮直接增加 Cocotron 的 `CGFloat.c`、`CGContextNativeLayer.m` 和 `CALayerContextNative.m`。后者创建真实 RGBA 位图，让原版 CALayer 的 `renderInContext:` 渲染图层树，并实现快照、尺寸变更、清空、定时器和失效处理。它是独立的 CALayerContext 类，没有把 CAContext 改名。原版 QuartzCore 仅增加两个明确的类符号重导出，原有机器码和导出保持不变。NSView 的图层托管、自动 backing layer、尺寸变化和销毁也已通过实际调用验证。窗口绑定、OpenGL 纹理及 Metal 渲染仍不支持。

CoreGraphics 辅助接口保留 Onyx2D 原始物理坐标变换，将 Base CTM 元数据与当前绘图状态分开保存。已验证非单位变换、状态保存/恢复和实际绘制像素；没有声称整个 CoreGraphics/QuartzCore 都兼容。浮点有效性判断对 18,206 个位模式与原版 Intel 指令做差分，包含信号 NaN、无穷、次正规数和全部指数边界，同时检查浮点异常标志。

完整的八文件 Darling libtrace 已独立重编，加入 `os_log_compare_enablement`。25 种有效级别组合与原版排序差值一致，原有 21 个编译器编码日志场景、格式错误拒绝及实际 ASL 输出继续通过。`os_log_copy_message_string` 使用之前恢复的原版 Intel trace 实现，经延迟加载转接传入原始消息指针；已验证整数、浮点、序列化字符串及私有数据池。原始私有池存在时会格式化其内容，缺失时输出 `<private>`；这里不提供采集权限或隐私授权机制。

最新组合下，原版 lsd 仍在测试前后存活，完整的当前 Swift UTI 客户端仍通过。原版 xcodebuild 的摘要与 XIP 解压结果一致。该历史检查点的 SDK 列举返回 255，缺失 `os_log_set_hook`，当时的 getter 和 fault callback 也仍是断言路径。这些接口已由上方的九文件源码流程推进，旧检查点保留作对照。

源码补丁分别保存在 `artifacts/darling-native-layer-source.patch` 和 `artifacts/darling-libtrace-enablement-source.patch`，已对各自源码子仓库反向校验。图形补丁同时包含此前 CGS/CA render server 源码依赖。历史八文件重建命令已由上方九文件流程替代。原版图层和格式化结果保留在 `artifacts/layer-log-progress.json`，旧运行库保留用于隔离回归。当前仍为源码组件与选择性兼容库混合运行；原版日志库使用延迟加载，强制立即解析所有无关接口还会遇到 LoggingSupport 的 `__dyld_dlsym_blocked` 缺失。

## 源码运行库与 LaunchServices（此前检查点）

此前底层源码补丁是 `artifacts/darling-mount-metadata-statfs-ext.patch`，覆盖之前的元数据修复和后续挂载适配，可对当前 XNU 子仓库反向校验。共享属性查询使用真实 Linux statx、扩展属性及目录项，按 Darwin 位图和记录规则打包。挂载枚举、路径与 FD 查询统一文件系统标识，并把物理挂载名转换回 Darling 虚拟路径；例如实际 Linux `/state/prefix` 在 Darwin 中返回 `/`。公共挂载解析器处理带空格的名称、长选项及路径前缀边界；打开后删除的文件也能查询其文件系统。

`statfs_ext` 和 `fstatfs_ext` 已加入 Darling 的真实 libsyscall CMake 源码列表，使用固定提交的 [Apple XNU 原始实现](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/libsyscall/wrappers/statfs_ext.c)。除 Darling 头文件适配入口外，包装实现保持一致；来源和摘要在 `vendor/apple-xnu-statfs-ext/reference.json`。当前旧属性后端不认识新增卷字段，会返回 EINVAL，原始包装器随后按其已有逻辑回退到真实 statfs/fstatfs；这不是不访问底层文件系统的 NOBLOCK 实现。

LaunchServices 实际引用的 17 个 ContainerManager 接口经独立 libSystem 命名重导出、延迟解析和 x86_64 寄存器保留跳转，进入未改动的原版实现。已核对全部目标地址，并验证 256 个真实查询对象的创建、配置和释放。没有伪造容器记录或查询成功；原版 `lsd` 的 remote-placeholder 查询仍可报真实错误并继续执行。

原版 `lsd` 现在能完成本次初始化并在测试前后保持运行，通过真实 Mach/XPC 路径向客户端发送 CSStore 数据。当前原版 Swift UTI 客户端的四种类型标识、首选扩展名、URL 扩展名、对 `.data` 的继承关系，以及 PNG 扩展名和 JSON MIME 反查全部通过，见 `artifacts/native-lsd-mount-path-container-manager-metadata-kernel-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json`。这不代表已审计全部 CoreTypes 声明、所有 LaunchServices 服务或容器权限。原版 translocation 服务仍未启动成功。

底层元数据验证保持 11,444 项断言；真实 bind/tmpfs 挂载与扩展 statfs 验证通过 2,497 项断言，覆盖名称转义、相似前缀、删除后 FD、路径往返和原始包装器的回退/错误行为。断言数包含逐字节检查，不代表同等数量的独立场景。挂载测试直接对比运行前后的宿主 mountinfo，确认宿主挂载表未改变。完整证据见 `artifacts/mount-container-progress.json`。

实验版本独立于默认入口；已有本项目依赖和框架暂存结果时，可按顺序重建、复查：

```bash
python3 scripts/build-libsystem-kernel-source.py \
  --output-dir runtime/mount-path-kernel-source \
  --variant-base runtime/metadata-kernel-source/darling-root \
  --report artifacts/mount-path-kernel-source-build.json
python3 scripts/stage-container-manager-export.py
python3 scripts/test-mount-path-kernel.py
python3 scripts/test-metadata-kernel.py --mount-path-kernel
python3 scripts/probe-container-manager.py --mount-path-kernel lifecycle
python3 scripts/probe-container-manager.py --mount-path-kernel foundation
python3 scripts/probe-container-manager.py --mount-path-kernel version
python3 scripts/probe-native-lsd.py --source-libtrace --user-local-dir-export \
  --rootless-datavault-export --sandbox-container --with-dirhelper \
  --native-sysdir --metadata-kernel --native-container-manager --mount-path-kernel
python3 scripts/probe-container-manager.py --mount-path-kernel showsdks
python3 scripts/record-mount-container-progress.py
```

以上历史配置的 `showsdks` 仍按实际失败返回 255。该底层源码检查点取代之前的 `metadata-kernel-progress.json`；旧版二进制和报告保留作历史证据，旧记录脚本不会覆盖当前状态。内核仍有批量枚举的共享 FD 偏移锁、完整无效属性错误记录、跨挂载语义、挂载标志/所有者映射及跨 overlay 挂载的稳定标识等限制。当前仍为源码组件与兼容/重导出库混合运行，不是全量统一重编 Darling；原版 xcodebuild 未修改。

## 使用

```bash
cd /home/dl/linuxcode
./bin/xcodebuild -version
./bin/pod --version
./bin/darling shell
./scripts/smoke.sh
./scripts/test-xcode-tools.sh
./scripts/test-swift-runtime.sh
./scripts/test-cocoapods.sh
```

将项目内 `bin` 加入 PATH 后，可以保留命令名称和参数：

```bash
export PATH="/home/dl/linuxcode/bin:$PATH"
xcodebuild -version
```

该入口保留当前项目子目录并转发到 Darwin 内的原版 xcodebuild。Darwin 内 `/usr/bin/xcodebuild` 是一个小型启动脚本，按 `DEVELOPER_DIR` 或 `xcode-select` 选择原版程序，绕过 Darling 原有入口与 Xcode libxcrun 的版本检查冲突。实际 Apple xcodebuild 二进制未修改。

在 Darwin 环境中运行已有 CI 脚本：

```bash
./bin/darling shell /bin/bash /Volumes/SystemRoot/workspace/ci.sh
```

项目在独立 Linux 根文件系统中为 `/workspace`，在 Darwin 中为 `/Volumes/SystemRoot/workspace`。宿主机任意目录和环境变量不会自动传入。完整 CI 的 CocoaPods、资源处理、归档、签名和导出仍需分别验证。

## 实测结果

| 检查 | 结果与证据 |
| --- | --- |
| Darwin shell、Python plist/XML、Ruby JSON | 通过；`logs/smoke-*.log` |
| 文件持久化、退出码、主机隔离 | 通过；`logs/host-smoke.diff` 为空 |
| 原版 `xcodebuild -version` | Xcode 26.6 / 17F113；`logs/xcodebuild-version.log` |
| 原版 clang/ld 编译链接 iOS C 程序 | 通过；`artifacts/hello-ios`，ARM64/iOS Mach-O |
| 原版 clang++ 编译链接 STL/异常处理程序 | 通过；`artifacts/hello-cpp-ios` |
| 原版 dsymutil | 通过；`artifacts/hello-cpp-ios.dSYM` 含 DWARF 子程序信息 |
| 原版工具链编译链接 macOS 程序，并在 Darling 运行 | 通过；`artifacts/hello-macos`、`logs/hello-macos-run.log` |
| 32 个并行任务竞争真实 unfair lock | 通过；`logs/dispatch-lock-regression.log` |
| Darwin CocoaPods 1.16.2 与原生 FFI | 通过；`logs/cocoapods-version.log` |
| 本地 Pod 安装、workspace 与 Pods 工程生成 | 通过；`logs/cocoapods-install-fixture.log`、`logs/cocoapods-project-verify.log` |
| CocoaPods CDN HTTPS 与 TLS 证书校验 | 通过；`logs/cocoapods-https-probe.log`、`logs/tls-verification-probe.log` |
| 原版 Swift 6.3.3 前端编译、链接、执行 | 通过；集合、Foundation JSON、8 个异步任务求和；`logs/test-swift-runtime.log` |
| CryptoKit 原版 SDK 客户端 | P256 签名、有效/篡改消息验证、SHA256 标准向量通过，Linux OpenSSL 独立验签通过；`artifacts/cryptokit-compat.json` |
| Combine 原版 SDK 客户端 | map/catch、延迟 Future、需求计数、取消、类型擦除通过；`artifacts/combine-compat.json` |
| Swift System 原版 SDK 客户端 | 文件路径、文件读写、错误码通过；`logs/system-client-execute.log` |
| AppleArchive C/Swift 文件流 | 实际读写、随机访问、取消、选项通过；解压、归档编码和提取尚未实现，明确失败 |
| 原版 Apple Swift demangler | 加载、反解名称、模块查询及非法输入检查通过；`logs/demangle-client-execute.log` |
| Swift UTI 原版 SDK 客户端 | 标识符、SDK 文档中的继承关系、哈希与编码往返通过；`artifacts/uniform-types-compat.json` |
| 原版 Swift 驱动 | `swift --version` 通过；`logs/swift-version.log` |
| SoftLinking | 真实库加载、备用路径、合并错误信息、调用方 `@rpath` 均通过；`artifacts/softlinking-compat.json` |
| OSAnalytics | 仅已核对的常量及 NSError 失败接口；报告转换和符号化未实现，不生成占位报告 |
| 原版 Apple CoreEntitlements | 重建后实际 DER 序列化/解析、正反子集比较、非法数据拒绝、两份异址副本、独立 Python/OpenSSL 解码与标准安装路径调用通过；`artifacts/coreentitlements-compat.json` |
| 原版 spindump | 默认 Mach-time 阈值初始化通过；采样与报告生成未验证；`artifacts/spindump-compat.json` |
| 原版 AMSupport / FDR | Base64、数字转换、实际类型注册和内部 MD5 向量通过；设备身份、联网与工厂数据操作未验证 |
| 原版 RemoteServiceDiscovery | 7 个类和原始协议注册、查询对象初始化/属性复制/释放、NSData SHA256 向量通过；设备发现及连接未验证 |
| `xcodebuild -showsdks`、最小工程 build | 失败；默认环境缺 NaturalLanguage；52 库实验路径缺 Foundation.Morphology，尚未进入工程构建阶段 |
| actool | 失败；缺 CoreSVG |
| 真正的 Apple codesign | 失败；缺 AppleMobileFileIntegrity |

`scripts/probe-xcode.py` 重新探测完整 Xcode 路径，将退出码、日志位置和 Apple 二进制摘要写入 `artifacts/xcode-probes.json`；完整构建失败时返回非零。C/C++ 编译测试使用真实 Apple 编译器及 SDK；iOS ARM64 是输出架构，运行这些工具的宿主仍为 x86_64。

## Darling 兼容性修复

`scripts/apply-runtime-compat.sh` 可重复应用修复；原始 Darling 库保存在 `runtime/compat-backups/`，Apple Xcode.app 保持原样。

- 官方包漏装 Expat：用固定版本开源源码补编译，恢复 Python XML 功能。
- 官方包中的 44 个 Swift dylib 实际是 Git LFS 指针：下载真实文件并核对 SHA-256 和长度。
- 现代 Swift：从 Swift.org 官方 Swift 6.3.3 macOS 安装包提取真正的标准库，核对包 SHA-256 和 XAR Payload 摘要，放入隔离前缀。为旧 Foundation overlay 补回真实 Objective-C ABI 掩码查询。原版 Xcode 前端、Foundation 和并发执行均已验证。
- CryptoKit：将固定版本 Apple swift-crypto 3.15.1 的实际软件实现编译成 Darwin 框架，使用其 BoringSSL；匹配当前导入的 Swift ABI。没有替换原版编译器或 xcodebuild。独立原版 SDK 客户端及 Linux OpenSSL 验签通过。
- Combine：将固定提交 OpenCombine 的实际核心实现编译为稳定 ABI 框架，按 SDK 对齐已冻结的布局与盒子初始化名称。DVTFoundation 引用的 40 个符号全部具备。Foundation/Dispatch 调度适配与 KVO publisher 尚未实现。
- Swift System：固定 Apple swift-system 1.6.6 源码，编译为 System 模块，使用真实 Darwin 文件系统调用。
- AppleArchive：自行实现 C 文件/自定义字节流及 Swift 文件流/选项子集。Swift 归档解码、提取和解压入口打印未实现并返回失败；不提供成功占位结果。没有证明 Xcode 归档流程可用。
- Swift demangler：复用 Xcode 自带原版实现的副本，只调整副本安装路径。
- Swift UniformTypeIdentifiers：从原版 SDK 文档生成 128 个标识符及已声明的继承关系，实现 Swift 值查询。尚无 Objective-C 桥接、系统类型注册、标签查询和本地化描述；Apple 硬件型号查询明确不支持。Darling 原有 Objective-C UTType 占位实现没有修改。
- OSAnalytics：从原始恢复缓存核对三个常量的值，按原版转换方法的错误返回约定提供明确的 ENOTSUP NSError。崩溃报告转换与符号化未实现，也不将这一边界标为完整功能。
- SoftLinking：按原版 x86_64 控制流实现路径列表加载，通过 Darling 的真实 dlopen_from 保留调用方路径上下文。备用路径、真实函数调用、错误信息和调用方 @rpath 都已测试。
- CoreEntitlements：从已验证的 Intel 恢复缓存重建 Apple 原版 C/C++ 实现，恢复绑定、重定位和导出；所需 DER 函数同样恢复自原版 corecrypto。类型化分配转发到已有 malloc/operator new，保留真实分配及异常行为，忽略类型统计元数据。该项没有使用成功占位的权限检查。
- spindump、AMSupport、FDR、RemoteServiceDiscovery：从相同已验证缓存恢复原版机器代码。恢复两份库中的 Objective-C 类、元类、相对方法表、协议、分类、属性和实例变量元数据；清除缓存专属的预优化状态。补充的 XPC 空字典构造转发到真实字典 API，类型化 malloc/realloc/calloc 转发到真实分配器，Security 常量取原始缓存中的确切值。设备服务、远程连接及采样并未据此宣称可用。
- libc++ 缺 filesystem、verbose abort 和 bad_function_call 关键函数：补编译真实上游实现并重导出原库；空 std::function 抛出和捕获实际异常的回归通过。
- Foundation、CoreFoundation、PackageKit 缺现代入口：补齐常量、不可变集合 ABI，并重导出已有 Swift Foundation 实现。NSConstantIntegerNumber/NSConstantDoubleNumber 按原始 25G83 实现确认的布局继承 NSNumber；原版 Apple clang 生成的字面量经数值转换、CF 桥接、哈希和字典查找实测通过。
- Swift Context2 类型查找：仅在本环境的 x86_64 ABI 下转发给等价入口。
- os_log 缺日志入口：转发给实际日志实现。
- Apple Git 缺现代崩溃入口：补齐真正终止进程的 crash-msg 入口。send-and-compose 格式化仍未实现，如果执行到该入口会明确报错并终止；没有返回成功的占位实现。
- libcurl 的 Heimdal 依赖缺三个 corecrypto 尺寸查询入口：按 Darling 当前开源结构实现查询，恢复 HTTPS 库加载；没有实现或替代底层 DH 密码运算。
- libRosetta 查询：在原生 x86_64 环境中正确返回未经过 Rosetta 翻译。
- 原版 ld 并行解析触发递归锁崩溃：libSystem 导出解析到了 libsystem_kernel 中空的弱锁函数。保留原库所有导出和依赖序号，新增两个显式重导出，指向 libplatform 的真正加锁、解锁实现。修复后并行回归和真实链接均通过。
- Darling 的 plist/sysctl 产品版本报告统一配置为 26.2，以通过版本门槛。这不代表 macOS 26 API 已实现；内核兼容层仍是 Darling。

这些修复不是完整的 macOS 兼容实现，也没有将未执行的签名或资源处理报告为成功。

## 新增的原始库与资源验证

原始 Swift `os` 库已恢复并安装。除 Objective-C 元数据外，还恢复其 286 处 Swift 跨映像相对引用，保留真实 Swift 发现区段；原版 SDK 客户端通过 Logger 开启查询、插值参数实际求值、反射、Hashable/Set、泛型锁状态修改和非平凡数组对象析构测试，并在标准路径下复测。所需 metrics 函数指向单独的原始 Apple 代码副本，仅注册四个 metrics 对象类，不接管已有日志/活动类及其加载初始化；维度对象创建、添加、容量拒绝和释放已验证。统一日志投递、计数器操作、遥测上报及 symptoms 守护进程通信仍未验证。见 `artifacts/swift-os-compat.json`、`artifacts/native-metrics-compat.json`。

CoreEmoji 与 libsystem_featureflags 的原始机器代码已重建并安装到隔离前缀，实际 U+1F600 正例、ASCII/空输入反例，以及功能开关 plist 的开启、关闭、缺失配置测试均通过。已在标准安装路径、无 DYLD 路径覆盖条件下复测。`simple` 功能开关接口在没有系统共享表时，由原始 Apple 代码保留调用方默认值；没有伪造共享表或固定返回开启。

原始 `aa` 工具在 Darling 下，配合重建的 AppleArchive、ParallelCompression 和 compression 库，已从完整安装包的 53 个 PBZX/YAA 数据块提取三份框架资源。使用原版 `aa convert` 排除 Linux 目录不支持的所有者、模式、标志和时间字段，再提取资源字节；未把不支持的文件系统操作伪装为成功。按原始 `links.txt` 恢复 232 个资源硬链接，独立解析 465 份 plist，共记录 866 个资源文件的摘要。见 `artifacts/framework-reference-resources.json`。这几份压缩/归档库当前仍只放在实验目录，尚未替换系统 AppleArchive 子集。

缓存中的 TLV_Thunkv2 描述符已按 Apple dyld 的真实布局还原为 Darling 支持的磁盘 TLS ABI。MeCab 和 Lexicon 实际库的零填充模板在主线程及两个工作线程间保持独立，重复查询地址稳定；MeCab 两个 lattice 对象的创建、句子修改、请求标志与释放也通过。见 `artifacts/cache-tls-compat.json`。这些语言库仍在暂存目录，不能据此认定 NaturalLanguage 可用。

CoreML 已完成暂存加载及原始 MLFeatureValue API 执行验证，整数边界、浮点、字符串、未定义值、比较和复制通过。LLVM 可完整读取 Mach-O 和符号表；恢复了 1,175 处 Swift 相对引用、335 个 Objective-C 类及 TLS 描述符。代码分析使用原始 `LC_FUNCTION_STARTS` 的 16,674 个入口，以及项目内固定 SHA-256 的 Capstone 解码器；识别并验证 850 组尾部跳转表、5,169 个表项。破坏真实表项或覆盖表地址寄存器时，整组都会被拒绝，其他函数的结果不变。见 `artifacts/coreml-code-table-audit.json` 和 `scripts/test-cache-code-analysis.py`。已安装的 Swift os 和 RemoteServiceDiscovery 在共享重建逻辑更新后，结果均逐字节不变。

MLCompute、MIL、RunningBoardServices、MLAssetIO、MetalPerformanceShadersGraph 等依赖也已暂存并通过 LLVM 结构解析。CollectionsInternal 新恢复了非拷贝类型发现记录和 resilient 类构造模板；实际执行 `_HashTable.Header`、`_DequeSlot`、`_HashTable.Storage` 的原始元数据访问器，完成类型构造、重复访问、原始描述符身份和类型名反射测试，见 `artifacts/collections-metadata-compat.json`。容器操作、泛型及非拷贝类型执行尚未验证。CoreML 特征值客户端已由原版 Xcode 编译器编译并实际执行通过；模型编译和推理仍未验证。这些实验没有安装到系统框架路径，完整 Xcode 构建和签名仍未通过。

APFS 的三个 Fletcher64 SIMD 实现在 17 种长度、三种输入对齐和四个初始状态下，与独立标量取模算法完成 612 组比对；代码段内的向量常量逐字节核对摘要，并验证真实读取指令覆盖完整范围。AppleKeyStore 的 28 个原始 Swift 字符串已在实际重定位后的映像中读取，UTF-8、值比较及写时复制均通过；IOKit 默认端口常量按原始四字节零值恢复。见 `artifacts/apfs-fletcher-compat.json`、`artifacts/applekeystore-string-compat.json`。磁盘、密钥存储、硬件服务及签名能力尚未验证。

原始 Swift Dispatch 保留旧库全部 640 个导出。实验适配补齐零字段 executor 基类和 Foundation 初始化依赖，并把两种 executor 的 job 分别交给真实 GCD 和 Swift 运行时执行。原版 SDK 客户端通过队列专属值、64 个异步任务、信号量超时、异常传播、自定义 actor 的 64 次状态修改，以及指定并发 TaskExecutor 上的 64 个子任务；实际 Swift executor 上下文也经过检查。真实 C 数据事件队列通过，Exclaves 通知源创建明确返回 `ENOTSUP`。见 `artifacts/swift-dispatch-compat.json`、`artifacts/dispatch-executor-compat.json`。完整 QoS、计时器和事件源覆盖仍未验证；这些库仍只在实验搜索路径下启用。

CoreServices、LaunchServices、CoreServicesStore 和 IOSurface 的原始 Intel 映像已完成暂存重建。原版 Metal 的 `MTLResidencySetDescriptor` 已实际执行默认值、标签复制、对象复制及实例状态隔离测试，并检查方法实现确实来自暂存的 Metal；见 `artifacts/metal-descriptor-compat.json`。这不包含 GPU、设备、驱动或着色器执行验证。

另有 82 个原始 CFString 标识符经过源码映像摘要、真实常量对象类型与字节验证；实际运行通过类型、值比较和独立复制。容器 persona 字符串、sandbox 的 32 位标志及自身地址 token 也按原始表示恢复，没有提供相应容器或 sandbox 服务。原版 Apple clang 生成的 `NSConstantFloatNumber` 常量通过字段布局、负零、最大值、最小非零值、CF 桥接和字典查找测试。复用固定提交的 Darling 分支 `NSPersonNameComponents`，通过中文字段、复制、音标字段隔离及安全归档往返。见 `artifacts/native-string-constants-compat.json`、`artifacts/constant-float-compat.json`、`artifacts/person-name-compat.json`；这些兼容库均未全局安装。

Swift Accelerate 的新映像已恢复 25 条 Swift 类方法覆写记录，并通过 LLVM 结构解析；尚未完成加载或 API 执行验证。它提供了 CoreML 所需的新 BNNS 元数据，同时暴露出 Darling Accelerate 中缺失的更多真实数值/图像函数。姓名格式化复用固定 GNUstep 源码并作局部适配，验证基础/英文 locale 的样式、缺失字段、组合字符首字母、音标及复制；其他 locale 和组件标注明确抛出异常，解析与归档兼容未建立。见 `artifacts/person-name-formatter-compat.json`。

新版 UserManagement 的 NSMachPort 类及元类绑定已改向已有 Foundation 实现。实际方法归属检查、Mach rights 创建、run loop 空消息及 OOL 数据消息收发通过；失效后仍观察到 SEND/RECEIVE rights，测试主动清理，未认定完整所有权兼容。Darling 自带 NSXPC 编解码类原本是隐藏符号；暂存 FND 副本仅扩展四个类及元类导出，保留原始指令、类元数据和全部 1,595 个已有导出。原版 SDK 客户端核对类身份，实际完成 bplist16 标量 invocation 编码、解码、调用与畸形数据拒绝。见 `artifacts/mach-port-compat.json`、`artifacts/foundation-xpc-exports.json`。没有新增同名 NSMachPort 或 NSXPC 类，也没有全局替换 FND。

XPC send-once 适配遵循固定原始 Intel 例程的权利接管、保留式复制、原子提取和释放行为，实际测试创建真实 Mach send-once right、发送并消费消息、未提取时释放，以及错误类型和重复提取处理。该类型的 XPC wire 序列化尚不支持。见 `artifacts/xpc-send-once-compat.json`。

完整 Intel 参考中的部分数值库标记为 `x86_64h`。Darling server 原来固定报告通用 subtype，导致加载器回退到旧库；仅在项目内修正三个 CPU 报告常量值，并在每次启动前核实实际 Haswell 指令集和 OS XMM/YMM 状态。原版 Apple clang 生成的同一个 AVX2 动态库在修正前明确被拒绝，修正后实际执行通过；基础工具链、Swift、CocoaPods 与主机隔离回归通过。未更改宿主内核或 Apple 工具二进制，见 `artifacts/host-cpu-compat.json`。启用这组完整参考实验后，当前运行时需要满足该硬件/OS 检查。

原始 Accelerate、vecLib、vImage、BNNS 和 vDSP 已暂存。保留 vDSP 的 149 组原始 stub/resolver，实际调用公开入口及原始 CPU resolver，通过 306 组浮点向量长度/正负步长比对和双精度加法；原始 BNNS 编译选项的默认值、读写、对象隔离和销毁，以及 vImage 带行间距的字节/浮点/字节图像往返通过。见 `artifacts/native-accelerate-cpu-compat.json`。这些不包含模型推理、图编译、GPU 或全部数值 API 验证。

ODIE 及其 MLModelAsset、Swift Metal 依赖已完成严格暂存重建；六个非泛型原始元数据访问器的完整状态、精确描述符、类型名和缓存身份验证通过，见 `artifacts/native-swift-metadata-compat.json`。Swift Metal 同时恢复了无类映像中的 Objective-C 协议/分类。CoreML 加载及特征值 API 已通过，Metadata 和 MetadataUtilities 已恢复，40 字节线程局部模板通过三个并发线程的初始化和写入隔离验证。原始暂存路径下 `xcodebuild -showsdks` 当前缺 Foundation.Morphology 的枚举常量。`scripts/audit-runtime-symbols.py` 根据当前搜索路径和真实导出/重导出链检查绑定，区分立即/延迟与强/弱符号；链式 fixup 和特殊全局查找明确列为未检查。搜索路径的静态推测不能代替实际加载路径、CPU subtype 及 API 执行验证。

新增验证入口为 `scripts/test-constant-numbers.sh`、`scripts/test-feature-flags.sh`、`scripts/test-core-emoji.sh`、`scripts/test-cache-tls.sh`、`scripts/test-swift-os.sh`。已有完整参考缓存和资源时，`scripts/prepare-core-emoji.sh` 重建、验证并安装 CoreEmoji；`scripts/prepare-reference-resources.sh` 可从已下载的固定安装包重新提取资源。`scripts/prepare-swift-os.sh` 重建并测试新的 Swift os 和独立 metrics 副本。这些脚本需要已有 Darling/Xcode 基础环境；已启用的完整参考模块会由后续 setup 重建保留，基础 setup 本身不会默默下载完整系统安装包。

## 系统框架与共享缓存

已从 Apple 公共恢复服务下载 Intel macOS 26.6.2（25G83）恢复镜像，验证全部分块 SHA-256 和 Apple 签名 chunklist。原始文件在 `downloads/recovery/`。无需 Mac，也没有启动 macOS 或虚拟机。

此外，已下载 Apple 公共目录中的完整 Intel 安装包 140-93587（26.6.2 / 25G83），固定输入位于 `config/apple-installer-25G83.json`。包、SharedSupport、MobileAsset ZIP 和 Intel RIDIFF 补丁的摘要均有记录；包内签名 CMS 未验证。原始 Apple RawImagePatch 在 Darling 内完成 RIDIFF 解码并通过其逻辑摘要校验；Linux 上用开源 libzbitmap 解码 APFS 压缩流，获得七份 Intel 缓存。全部 1,404,360 个 4 KiB 代码页均符合内嵌 CodeDirectory 的 SHA256；篡改一个字节会被检查拒绝。缓存签名为 ad hoc 且 CMS 为空，这不等于 Apple 证书链验证。

**完整 APFS 文件的 SHA384 与 BuildManifest 的预期值仍不一致，原因尚未查明。** `artifacts/intel-system-image.json` 明确记录 `apple_manifest_digest_verified: false`。当前仅将其作为缓存提取参考；不宣称整个系统镜像等价、可启动或已通过系统签名验证。原始提取器从这组缓存导出的 3626 份文件放在 `runtime/fullsystem-libraries/`，仍需逐份恢复绑定及元数据，不能直接安装。重现参考缓存提取的入口为 `scripts/prepare-intel-system-image.sh`。

原版 Xcode dsc_extractor.bundle 已在 Darling 内成功提取 719 个缓存映像，位于 `runtime/recovery-libraries/`。它们用于分析，**没有安装到 Darling 系统目录**。实际 dlopen CryptoKit 失败，提示 `dyld chained fixups info underruns __LINKEDIT`，见 `logs/recovery-cryptokit-load.log`。

Apple 提取器会移除绑定信息；提取到文件不等于恢复独立可加载 dylib。目前现代 Swift 使用官方独立运行库，CryptoKit/Combine 使用开源的实际实现补充 Darling 系统兼容层，已经执行原版 SDK 客户端验证。另已针对多个固定映像完成独立重建；这不是通用共享缓存装载器。一手源码：[Apple 缓存提取器](https://github.com/apple-oss-distributions/dyld/blob/main/other-tools/dsc_extractor.cpp)、[缓存 fixup 说明](https://github.com/apple-oss-distributions/dyld/blob/main/doc/CacheBuilder.md)。

CoreEntitlements 的重建脚本恢复原始缓存 v2 指针链、58 个合并 GOT 指针槽、178 处 RIP 引用、71 处重定位及 62 个导出，并生成传统 dyld 绑定流。映像采用零首选基址，实际装载时重新定位；测试在同一进程装入两份不同地址的副本，均完成实际运算。所需的 8 个公开 DER 入口连同 7 个内部辅助函数保留原版机器代码及内部相对位置，只重新绑定 memcpy。相关实现为 `scripts/rebuild-coreentitlements.py`、`scripts/extract-der-functions.py` 和 `scripts/prepare-coreentitlements.sh`，实验中间产物保留在 `runtime/rebuilt-*`。

共享重建逻辑位于 `scripts/rebuild-c-cache-image.py`，对每个原始映像严格核对 SHA-256，遇到其他版本会明确失败。支持范围由 `config/cache-image-pins.json` 固定映像清单约束；Objective-C 元数据还使用 `scripts/restore-objc-metadata.py`，不支持任意外部协议/类的复制。Swift 映像需显式启用实验参数，由 `scripts/restore-swift-metadata.py` 恢复已支持的布局，并另行执行实际客户端验证；文件重建成功不代表 Swift 框架兼容。`scripts/prepare-coreml-experiment.sh` 可重建、暂存并诊断 CoreML/MLCompute，加载失败会记录 `artifacts/coreml-experiment.json` 并返回失败状态。已验证的权限数据包含字典、数组、字符串、整数、布尔值；长度越界、截断和重复键均被原版验证器拒绝。独立 Python 解码器和 Linux OpenSSL 另行检查输出。完整 App 签名仍未通过。

AMSupport/FDR 恢复原来的延迟函数指针；RemoteServiceDiscovery 还恢复已合并到缓存 GOT 的函数调用桩。只有原始 `S_SYMBOL_STUBS` 中的标准间接跳转可以延迟绑定；取地址、弱可用性检查与数据引用保持立即绑定。绑定器使用 Darling 的真实 `dyld_stub_binder`。测试除实际执行 Base64、查询对象和 SHA256 外，还强制调用缺失的 `SecTrustCopyCertificateChain` 入口，确认 dyld 报缺符号并终止，没有伪造证书链。这个接口、RemoteXPC 和设备服务仍有缺口；实验性证书链适配因底层安全服务阻塞而未安装。

CryptoKit 的实际执行与 Xcode 使用相同的惰性绑定方式；严格 `RTLD_NOW` 全量绑定仍会暴露旧 Swift CoreGraphics overlay 的 9 个缺失函数，见 `logs/cryptokit-library-load.log`。因此没有将整个系统框架兼容性标为通过。使用的实现与适配代码分别在 `vendor/swift-crypto-3.15.1`、`vendor/OpenCombine`、`vendor/swift-system` 和 `scripts/`，上游源码保持原样，生成的适配副本在 `runtime/`。

独立重建和验证这些组件：

```bash
./scripts/prepare-swift633-runtime.sh
./scripts/prepare-swift-system.sh
./scripts/prepare-cryptokit.sh
./scripts/prepare-combine.sh
./scripts/build-applearchive.sh
./scripts/build-applearchive-swift.sh
./scripts/prepare-uniform-types.sh
./scripts/build-osanalytics.sh
./scripts/build-softlinking.sh
./scripts/prepare-coreentitlements.sh
./scripts/prepare-remote-service-discovery.sh
./scripts/test-swift-runtime.sh
```

`scripts/inventory-runtime-dependencies.py` 对原版 xcodebuild 与 loader 的 Mach-O 加载命令建立静态依赖清单，报告在 `artifacts/runtime-dependency-inventory.json`。它采用每个映像首次遇到的 rpath 上下文，不覆盖全部 dlopen/插件路径，也不验证符号、ABI 或初始化行为，不能替代实际构建测试。

`scripts/inspect-dsc-constants.py` 可只读检查恢复缓存中的 ASCII CFString 常量；例如 OSAnalytics 的真实选项名是 `xform-trace`，不是根据导出符号猜测的名称。它使用 vendor/DyldExtractor 的结构定义，仅用于分析，不会安装提取库。

恢复镜像中的真实 codesign 也已单独探测，缺失 AMFI 框架。Darling 自带 codesign 明确是占位程序，因此本环境的 codesign 入口转发到真实 Apple 程序；真实程序不可用时明确失败。签名验收必须包含真实签名产物和独立验证；目前没有这样的产物。

资源工具还需要 CoreSVG 等依赖。Unity 导出工程、远程 Pod 的完整下载构建、Storyboard/XIB、Metal、App Extension、归档和 IPA 导出均未通过端到端验证。

CocoaPods 的 39 个依赖包锁定在 `config/cocoapods-gems.lock.json`，逐个验证 SHA-256。执行使用 Darling 的 Ruby 2.6.3 和 Intel Darwin FFI，RubyGems 更新到兼容版本 3.4.22，补回 Darwin gem 目录惯例及已内置 JSON 2.1.0 的默认 gem 注册。运行环境设置 UTF-8；命名空间内 UID 为 0，因此设置 CocoaPods 官方支持的 COCOAPODS_ALLOW_ROOT，宿主机身份仍为当前普通用户。

CDN 已成功下载 AFNetworking 4.0.1 的 podspec，内容与独立 Linux HTTPS 下载逐字节一致。一次完整目录查询在另一个旧版本 1.0RC1 的 URL 上超时，因此尚未将远程 Pod 下载整体标为通过。详细状态在 `artifacts/cocoapods-probes.json`。

```bash
./scripts/setup-cocoapods.sh
./scripts/test-cocoapods.sh
```

重新准备恢复镜像分析材料：

```bash
./scripts/prepare-recovery.sh
```

## 重建

```bash
./scripts/setup-xcode.sh /path/to/Xcode_26.6_Universal.xip
```

首次会建立 Ubuntu 根文件系统、解压 XIP、导入 Xcode、应用兼容修复并运行基础、工具链、Swift 和本地 CocoaPods 测试；最后另行记录完整 Xcode 路径的失败或成功。基础安装脚本完成不代表完整构建验收通过。XIP 的 XAR Content 摘要已校验；提取器未实现 XIP 外层 CMS 证书链验证。导入器不覆盖已有 Xcode，缓存保留在项目目录。

宿主机需要 bash、curl、git、unzip、tar、cpio、sudo、util-linux、Python 3、CMake、Ninja、OpenSSL、clang/clang++/ld64.lld/llvm-ar/llvm-ranlib/llvm-nm/llvm-install-name-tool/llvm-objdump/llvm-dwarfdump 19。安装脚本不向宿主机安装这些工具。Darling 发布 ZIP 和 Ubuntu 基础镜像使用固定 SHA-256；Ubuntu 依赖实际版本记录在 `logs/runtime-packages.txt`。

Darling 发布版为 v0.1.20260608，Debian 包为 0.1.20260609~noble，运行时提交 e947f0d5；补编译头文件固定为 Darling 60ba801decee7a00782f74f6be4c8ffb013f79ff。Ubuntu Base 为 24.04.5 amd64。

## 隔离范围与文件

不安装内核模块，不创建宿主机服务。运行时使用普通用户的 user/mount/PID namespace，内部 UID 0 映射到宿主机当前用户；binfmt_misc 注册仅存在于该命名空间。使用 pivot_root 并卸载旧根。安装依赖时的 sudo 仅作用于项目根文件系统；运行时不需要 sudo。setuid/setgid 位已移除。

项目目录可读写，网络与宿主机共享，并使用基础终端、随机数和 FUSE 设备。每条命令退出后销毁该命名空间及其进程，Darwin 文件保留。命令串行使用共享前缀。

| 路径 | 内容 |
| --- | --- |
| bin/、scripts/、fixtures/ | 启动器、重建与验证脚本、可复现小工程 |
| runtime/rootfs/ | 独立 Ubuntu 和 Darling |
| runtime/state/prefix/ | Darwin 文件系统、Xcode、持久化用户数据 |
| runtime/compat-backups/ | 修复前的 Darling 库 |
| runtime/recovery*/ | 恢复镜像文件和缓存分析材料 |
| vendor/、downloads/ | 源码、发布包与下载缓存 |
| logs/、artifacts/ | 实测日志、版本信息、编译产物 |

删除本项目的运行数据即可移除环境；宿主机没有需要卸载的 Darling 包、模块或服务。

原版完整 Foundation/CoreFoundation 的替换实验单独保存在 `runtime/foundation-native-framework-stage`、`runtime/foundation-native-library-stage`。`scripts/prepare-native-foundation-experiment.py` 严格重建并暂存固定映像，`scripts/probe-native-foundation.py` 记录真实加载错误。两个主要映像分别保留 15,511 和 3,074 个原始导出；Darling 旧库所需的 18 个 Foundation 名称额外按真实依赖重导出。原版 Foundation 已实际加载，部分 Objective-C 与 Swift API 执行通过；完整兼容性仍未验证，未安装到默认环境。Swift 参数包、条件参数包和混入类型引用区段的二进制泛型描述符已有结构支持；固定 Foundation 的 4、8、5 组实际记录及五种损坏记录拒绝检查通过，见 `artifacts/swift-metadata-layouts.json`。这些结构检查不代表运行时兼容。

完整 Foundation 的独立实验现有 30 个原版映像；目录、容器、sandbox 和 quarantine 实现也按原始 Intel 缓存恢复。原版 sysdir 目录枚举在 SDK 11/26.6 两种主程序标记下通过路径、域顺序及全部 16 种域掩码检查；原版 quarantine 对象的 257 组标志/越界/独立复制检查通过，未据此宣称系统策略或文件隔离生效。新增 Objective-C 枚举与 selector 查询、默认保护模式 openat、环境变量锁及 zone 分配兼容接口已有独立执行记录。独立入口标记纠正了此前的阶段判断：早先的缺符号发生在启动绑定，不能据此宣称 Foundation 初始化已执行。隔离 DNS 库身份、补齐栈/XPC 接口并恢复 AggregateDictionary 的 category 方法后，原版 Foundation 已实际 dlopen 成功；实际 API 验证仍在继续，尚不作为完整兼容证明。

栈采集复用固定 Apple Libc 提交中的实际帧遍历实现；仅适配现有 x86_64 pthread 和旧 dyld，未支持 ARM、远程线程或 signal/alternate stack。普通栈容量 0–64、四线程，以及 64 个真实 Swift 异步任务的任务 ID、非空栈和缓冲区边界验证通过。见 `scripts/test-thread-stack-async.sh`、`artifacts/foundation-libc-compat.json`。XPC 连接失效描述读取现有后端的真实取消状态，32 个真实连接事件和独立字符串所有权测试通过；代码签名要求接口明确返回 ENOTSUP，未伪造验证或成功。见 `scripts/test-xpc-connection-compat.sh`、`artifacts/xpc-rich-error-compat.json`。

30 映像实验的实际客户端已通过字符串/集合/JSON/日期/NSError/CoreFoundation，以及中文文件的原子创建、覆盖、读回和删除。覆盖后权限位实际为 0664，未宣称保留原属性。Swift 客户端通过 Morphology 六种数、rawValue/Hashable、Codable 往返及 AttributedString 复制。当前使用运行时自身的 OBJC_DISABLE_TAGGED_POINTERS 设置，但另外的运行时生成字符串格式化测试仍触发 tagged pointer 访问问题，不能视为完整修复。见 `artifacts/native-foundation-values.json`、`artifacts/native-foundation-swift.json`。

当前多数实现采用独立源码兼容库、实验 Mach-O 副本的导入重绑定和重导出，尚未整理成 Darling 上游源码补丁集。DYLD_INSERT_LIBRARIES 文件 I/O 插桩只用于诊断。`getattrlist` 扩展读取真实文件元数据，其他请求保留旧后端；statfs_ext/fstatfs_ext 使用 Apple 未改动的包装实现和原来的 EINVAL 回退。52 映像 CoreML 在 category 元数据修正后的独立回归通过。原版 Apple 链接器仍有偶发超时，日志保留在 `logs/native-foundation-swift-link-timeout-20261016T0810.log`；相同命令重跑通过，原因未修复。

新增的三个 QuartzCore 接口已直接写入 Darling/Cocotron 源码：`CARenderServerGetDebugOption`、`CARenderServerSetDebugOption`、`CARenderServerGetFrameCounter`。实现使用真实 bootstrap 服务发现、Mach 请求/回复、OOL 内存及统计 plist 解析；服务缺失时沿原版失败路径返回，不创建渲染服务。固定原版函数作为仅供测试的对照，90 次实际消息交换覆盖值、错误、畸形回复、send-once 死亡通知和端口引用；在旧 CoreFoundation 和独立原版 CoreFoundation 路径下均通过。测试对照代码未链接进运行用框架。见 `scripts/build-ca-render-server.py`、`scripts/test-ca-render-server.sh`、`artifacts/ca-render-server.json`。

IOKit 的 `kIOMainPortDefault` 也已加入实际 Darling 源文件及头文件，值与原版和 SDK 定义一致：NULL 表示请求默认端口，不代表已连接硬件。实际客户端通过新旧常量、原有 IOServiceMatching 实现归属及字典内容检查。上述改动采用源码组件增量编译，与已有 Darling 后端重导出连接，暂存于独立实验目录；未全量重编译 Darling，也未覆盖默认系统框架。源码补丁在 `artifacts/darling-quartzcore-render-server.patch` 和 `artifacts/darling-iokit-main-port.patch`。

可按以下顺序重新验证并接入组件。`probe-full-native-xcode.py` 核对 30 个映像、组件、原始后端和 Apple xcodebuild 的摘要后运行真正的 `-showsdks`；当前返回失败，报告保存在 `artifacts/xcode-full-native-foundation-probe.json`，不能作为工程构建或签名通过的证明。

```bash
python3 scripts/build-ca-render-server.py
bash scripts/test-ca-render-server.sh
python3 scripts/stage-ca-render-server.py
python3 scripts/stage-iokit-main-port.py
bash scripts/test-iokit-main-port.sh
python3 scripts/build-cgs-accelerator.py
bash scripts/test-cgs-accelerator.sh
python3 scripts/stage-cgs-accelerator.py
bash scripts/test-cgs-accelerator-headless.sh
python3 scripts/probe-full-native-xcode.py
```

CoreGraphics 的 `CGSAcceleratorForDisplayNumber` 已直接补入 Darling/Cocotron 源码及 CMake 列表，通过现有 `CGDisplayIOServicePort` 与 `IOAccelFindAccelerator` 查询真实后端。固定原版 SkyLight/CoreDisplay 代码确认两项输出分别为服务端口与 framebuffer index；服务端口由客户端缓存持有，调用方借用。独立受控后端测试使用真实 Mach 端口，验证别名、失败清理、1,024 次并发缓存查询及卸载后的引用回收。生产框架不含测试回调，保留 575 个原有导出；当前无显示设备环境的三个实际查询均返回真实失败。物理加速器、镜像显示和热插拔尚未验证，未据此宣称 GPU 支持。见 `artifacts/cgs-accelerator.json`、`artifacts/darling-coregraphics-accelerator.patch`。

原版 Xcode 的源码运行库探测仍以 255 退出，当前缺失的是 `responsibility_spawnattrs_setdisclaim`。此前 `_launch_service_stats_copy_impl`、enable/disable 接口已经直接写入 Darling libxpc 源码，并配套实现 launchd 控制请求分派及实际退出记录；旧 `_4ppse` 空桩保持原名，未作 ABI 不相容的重命名。原版字段和调用约定的分析在 `artifacts/launch-service-stats-native-analysis.json`。

继续追到 Mach VM 层后，实际最小程序确认原包的 `mach_make_memory_entry_64` 会进入 darlingserver 的 unsafe stub，退出该隔离会话。现在已建立独立的 **完整 darlingserver 源码构建**，直接修改其 Mach memory-entry 创建、映射、引用释放和共享映射记录；这不等于重建整个 Darling。依赖的 bison/flex/m4 只校验并解压到 `runtime/host-build-tools`，没有向宿主系统安装软件包。

源码服务端现通过实际匿名页共享、子区域、部分解除映射、只读映射及拒绝 mprotect 升级为可写、错误参数、地址复用身份核对、四线程共 32 次映射，以及父子进程通过 Mach 消息传递 memory-entry 权利后的双向读写检查。32 次生命周期测试后，跟随后续 VM 请求核对实际映射，服务端 backing-file 数量回到基线。现有客户端会直接执行本进程 munmap，因此这项回收是后续 memory-entry 操作触发的核对，并非即时通知。匿名页转为共享页时的复制与替换尚不能保证并发写入原子性；固定/COW/复杂对齐、父入口派生、导入未知的既有共享文件映射明确返回不支持。完整继承和最大执行权限策略也尚未实现。

测试通过 `LINUXCODE_DARLING_SERVER` 在单次私有挂载命名空间中替换服务端路径，原包二进制摘要保持不变，默认入口仍使用原包。源码服务端现已根据实际 CPUID 特性及 OS 启用的 XMM/YMM 状态决定是否报告 Haswell subtype；host/processor/preferred-user-arch 三处报告和实际原版 Apple AVX2 库执行检查通过。原版 `xcodebuild -version` 回归通过，仍有 host UUID 查询错误 78 的诊断。共享内存映射还增加了原版 libxpc 所需的 `VM_PROT_IS_MASK` 权限交集语义，已验证只读能力不会因此升级为可写。见 `artifacts/darlingserver-memory-entry.json`、`artifacts/darlingserver-memory-entry.patch`。

libxpc 现在也按真实 CMake 源列表完整编译了 39 个源文件，保留原包全部 630 个导出及其中 112 个 launch 重导出。共享内存类的创建、复制、Mach 端口所有权、页对齐长度、映射、`0xc000 + uint64 length + COPY_SEND` 序列化与反序列化已直接写入 Darling 源码；不是额外加载第二套 XPC 类。截断消息测试还修复了原反序列化器误用接收缓冲区容量、字符串越界读取，以及 pipe 返回字典引用所有权的问题。

实际测试包括 32 次对象生命周期、96 个带真实端口权利的畸形/截断消息，以及父子进程通过真正 XPC 字典和 OOL 端口描述符往返传递共享内存。只读保护、双向写入、双方释放对象并清空 autorelease pool 后映射继续有效、后续 VM 核对后 backing FD 数量返回基线均通过。测试检查实际加载库的 UUID，并确认默认原包会被该身份检查拒绝。**输入为未登记的既有 MAP_SHARED 映射时仍不支持**；当前验证的是 VM 分配匿名页路径，不能视为完整的公开 xpc_shmem 契约支持。

`LINUXCODE_LIBXPC` 通过挂载独立完整运行库目录供 Darling 的 OverlayFS 使用。早先的单文件 bind mount 会被 OverlayFS 的底层查找绕过，因此启动成功不构成源码库已加载的证据；该路径已替换，当前以 UUID 和真实 API 执行为准。编译器使用 Linux clang-19，链接器使用本机 Darling 中的原版 Xcode ld，以保留 upward libobjc 依赖及选择性重导出。没有使用 Mac，也没有替换原版 xcodebuild。补丁与证据见 `artifacts/darling-libxpc-shmem.patch`、`artifacts/libxpc-source.json`。

源码运行库仍是独立实验版本。旧外部 rich-error 连接适配库的 UUID/code guard 绑定原包 libxpc，连接接口需适配后才能在源码版本使用，不能直接沿用旧 guard。源码运行库下的完整 Foundation/Xcode 探测已越过统计及 Mach-O slice 接口，当前缺少 `responsibility_spawnattrs_setdisclaim`，见 `artifacts/xcode-full-native-foundation-source-probe.json`；SDK 列举、工程构建、归档和签名尚未通过。

launchd 现也完整编译了 16 个源文件（含实际 MIG 生成源及新增统计模块），通过 `LINUXCODE_LAUNCHD` 选择与源码 libxpc 一致的独立运行目录。统计记录直接来自 launchd 的成功 `wait4`，保存标签、实际启动时间、进程 unique ID、PID、退出状态及信号退出原因。没有把请求本身生成成统计事件，也没有对合成或匿名退出伪造记录。原版恢复镜像中的 Intel launchd 用于只读分析，确认 59 字节 wire 布局、标签索引、最新记录优先、溢出计数及读取后清空语义。

原版 `launchctl load/unload` 实际启动任务后，版本 2–6 均读到正确的 PID 和退出码 7；SIGABRT 任务读到真实信号编号 6。容量为 2 的环形缓冲区经过 4 个真实任务退出后，保留最后两项、丢弃计数为 2，下一次读取为空。还验证了重复启用、未知监测器、错误请求、只读共享缓冲区拒绝、普通进程伪造 PID 1 字典字段仍被实际 Mach audit trailer 身份检查拒绝，以及搭配旧原包 launchd 时真实接收超时会返回而不会永久挂住。见 `artifacts/launch-service-stats.json` 和 `artifacts/darling-launchd-service-stats.patch`。

这仍不是完整原版统计实现：37 字节基础记录之后的 22 字节平台扩展字段尚为零；不支持非 root entitlement 授权、jetsam 或平台资源指标。监测器最多 32 个，每个最多 2^20 项，控制请求接收超时为 5 秒。启动时默认仍用原包；源码服务端、libxpc 和 launchd 需一起选择。联合回归的 MachPort、44 映像 dyld 快照与原版 Xcode 版本查询通过，见 `artifacts/source-runtime-integration.json`。

Mach-O 的 `macho_for_each_slice` 与 fd 版本复用固定 Apple dyld 源码的 Universal 解析器、六个原始头部方法及两项 API，放入已有的独立 dyld 兼容库。增加了畸形 fat 提前返回时的映射释放、thin stop 初值、隐藏 ARM64 描述符的额外验证槽和提前停止处理。这部分仍是实验源码兼容组件，不是全量重建 Darling dyld。实际测试覆盖 thin32/64、fat32/64、16 个声明 slice 加一个历史隐藏 slice、fd 位置与所有权、错误码、384 次畸形文件拒绝后映射数量不增长，以及真实 Xcode 文件的三个 slice。只检查元数据，不执行 ARM；不作为完整 Mach-O load-command 验证。既有 3626 映像缓存解析、28 个架构名称案例与进程快照回归通过。见 `artifacts/macho-slices-source.json`。

```bash
bash scripts/configure-darlingserver-source.sh
bash scripts/test-memory-entry-source.sh
python3 scripts/build-libxpc-source.py
python3 scripts/build-launchd-source.py
python3 scripts/build-dyld-cache-introspection.py
bash scripts/test-macho-slices.sh
bash scripts/test-xpc-shmem-source.sh
bash scripts/test-launch-service-stats.sh
bash scripts/test-source-runtime.sh
LINUXCODE_DARLING_SERVER="$PWD/runtime/darlingserver-source-build/darlingserver/darlingserver" \
LINUXCODE_LIBXPC="$PWD/runtime/libxpc-source/libxpc.dylib" \
LINUXCODE_LAUNCHD="$PWD/runtime/launchd-source/launchd" \
    ./bin/xcodebuild -version
python3 scripts/probe-full-native-xcode.py --source-runtime
```

`libsystem_kernel` 现也能独立完整源码构建：从实际 CMake 列表编译 874 个 x86_64 单元，生成 libsyscall/MIG、emulation、服务端 RPC 和 libsimple，保留原包全部 1,362 个导出。构建入口为 `scripts/build-libsystem-kernel-source.py`，配置固定源码版本及原库摘要。`LINUXCODE_LIBSYSTEM_KERNEL` 与源码 server/libxpc/launchd 一起选择私有完整目录，默认运行库不变。产品版本 26.2 的既有可用性门槛配置在编译时显式保留，不表示实现了全部 macOS 26 行为。

源码路径中修复了 `execve.c` 的声明及脚本参数复制：缺少正确 `memchr` 声明会把 64 位返回指针当作 int 截断，脚本 argv 复制还会越过原数组的 NULL 终止项。构建中另将 libsyscall 专用头路径限制在该组件内，避免其 MIG 专用 `mach/string.h` 遮住 emulation 应使用的 libc 头。实际验证了加载 UUID、原包身份拒绝、spawn 文件动作/管道/信号掩码/进程组/退出码、错误后 errno 保留、select/pselect、普通 shebang、带空格与解释器参数的 shebang、纯文本脚本回退，以及原样 `/usr/bin/xcodebuild -version`。既有真实 Mach memory-entry 与 XPC/OOL 传输回归也通过。见 `artifacts/libsystem-kernel-source.json` 和 `artifacts/darling-libsystem-kernel.patch`。

新源码内核运行库下，原版 `-showsdks` 仍返回 255，缺少 `responsibility_spawnattrs_setdisclaim`。已核对原版 Quarantine 24 字节属性、上层 MAC policy 存储和独立 spawn descriptor，但执行层尚未消费这些扩展，也未实现子进程责任归属，不能视为该接口已经完成。新的独立探测不覆盖原先三组件运行库的报告。

```bash
python3 scripts/build-libsystem-kernel-source.py
bash scripts/test-libsystem-kernel-source.sh
python3 scripts/probe-full-native-xcode.py --source-runtime --source-kernel
```


`responsibility_spawnattrs_setdisclaim/getdisclaim` 与 PID/unique-ID 查询现已直接加入 Darling `src/quarantine`，完整构建两个源文件，保留原有 24 个导出并增加四个接口。上层 `posix_spawn` 已有 MAC extension 传递；现在补齐 emulation 的 descriptor，并验证实际 policy 数据。仅支持 version 1、24 字节、disclaim 位及空的其余字段；坏指针、畸形版本和不支持字段明确报错。两个服务端 RPC 追加在原有 80 项之后，原定义保持不变。disclaim 通过独立 checkout 请求随 exec 的 CLOEXEC 管道传递，确认 Linux exec 成功后才提交，失败不改变原归属。

实际原版 libquarantine 的 32 轮属性往返、交叉 getter、保留标志与错误码对照通过。父子进程测试验证普通 fork/spawn 继承、四轮 disclaim 子进程归属自身及孙进程继承、成功 SETEXEC、真实无效 ELF 触发执行失败后归属保留，以及同一进程随后普通 exec 不带入失败事务。子进程的 birth-based unique ID 与成功的真实 libproc 查询一致。未知 MAC policy 返回 XNU 的 ENOPOLICY，Darwin policy errno 单独传输，避免与 Linux 的 EOPNOTSUPP 混淆。原包 libquarantine 的否定对照被拒绝。见 `artifacts/responsibility-source.json`、`artifacts/responsibility-native-analysis.json` 及其中的三个源码补丁。

这实现了选定的进程归属兼容行为，没有实现 macOS TCC 授权/强制策略、entitlement、其他 MAC policy、caller override 或所有 launch-service 归属规则，也没有在原版 macOS 内核上做行为对照。记录保存负责进程的 PID、出生 unique ID 和 registry generation，不会按旧 PID 再查新进程；未强制制造 PID 复用测试。旧 libproc 对 PID 1 查询父 PID 0 会失败的限制仍存在；独立身份核对使用实际自负责子进程。

`LINUXCODE_QUARANTINE` 与其余四个源码组件一起选择完整的私有运行目录。原版 Xcode 在此路径下已越过 responsibility 导出，`-showsdks` 仍以 255 退出，当前缺少 `sandbox_extension_issue_file_to_process`。原有三组件联合回归及四组件源码 kernel 回归已在这次服务端/RPC 改动后重新通过。默认运行库与原版 xcodebuild 均未修改。

```bash
cmake --build runtime/darlingserver-source-build --target darlingserver -j8
python3 scripts/build-libsystem-kernel-source.py
python3 scripts/build-quarantine-source.py
python3 scripts/analyze-responsibility-native.py
bash scripts/test-responsibility-source.sh
python3 scripts/probe-full-native-xcode.py --source-runtime --source-kernel --source-quarantine
```


`src/sandbox` 现完整构建两个源码文件，保留旧模块 43 个导出名并增加六个现代 file issue/consume/release 包装接口。按固定原版 Intel libsystem_sandbox 核对，四个 APP_SANDBOX 对象应为 `const char*` 指针，DEFAULT/CANONICAL/PREFIXMATCH/NO_REPORT 应为 uint32_t；原实现误把字符串对象定义为数组，并把相邻两个 32 位常量拼成了 64 位值。新源码修正了这些数据 ABI，旧的错误布局调用方尚未穷尽验证。

这些现代接口实际封装 `__mac_syscall("Sandbox", 5/6/7, args)`。Darling 服务端目前没有 Sandbox MAC policy，正常申请、消费和释放会沿真实系统调用返回 ENOPOLICY；没有把它们改为成功。原版 flag 1 路径在用户态分配 0x3ff0 字节缓冲区，用 strlcpy 写入 `invalid` 标记，消费该标记返回 0；它不授予访问权限。128 个正常申请失败、32 个原版 unresolved 标记、32 个消费失败及 32 个释放失败的源码/原版对照通过，同时核对四个指针和四个 uint32 数据对象、实际加载 UUID及旧模块否定对照。原版 Xcode 版本查询在六组件运行库下通过。见 `artifacts/sandbox-source.json`、`artifacts/sandbox-extension-native-analysis.json`、`artifacts/darling-sandbox-extension.patch`。

**这里没有实现真实 extension 授权。** 目标 audit token 验证、令牌能力及消费/释放生命周期、完整 Sandbox 策略和 VFS 强制检查仍待实现；旧 sandbox_init/check 的成功空桩仍然存在，不能作为沙箱有效的证据。当前进展是修正并接通用户态 ABI，且在策略缺失时保留实际错误。`LINUXCODE_SANDBOX` 与前五个源码组件一起选择完整私有目录，默认库不变。原版 `xcodebuild -showsdks` 已越过 sandbox extension 导出，当前以 255 退出并缺少 `xpc_connection_copy_invalidation_reason`；SDK 列举、工程构建、归档及签名仍未通过。

```bash
python3 scripts/build-sandbox-source.py
python3 scripts/analyze-sandbox-extension-native.py
bash scripts/test-sandbox-source.sh
python3 scripts/probe-full-native-xcode.py --source-runtime --source-kernel --source-quarantine --source-sandbox
```


`xpc_connection_copy_invalidation_reason` 现直接加入 Darling libxpc 源码，读取实际取消状态，返回独立的 strdup 字符串。取消字段改为 C11 atomic_bool，初始化为 false，在真实 DISPATCH_MACH_CANCELED 事件回调前发布为 true；其他线程用 acquire 读取。返回值只描述当前后端实际具备的取消状态，没有伪造现代详细错误原因。新增 peer code-signing requirement SPI 明确返回 ENOTSUP，不修改连接，也不表示实施了消息签名检查。完整 39 源文件构建保留原有全部 630 导出名及 112 个 launch 重导出，目前共 637 个导出。

旧 `libDarlingXPCRichError` 的连接入口会先查找与 xpc_connection_cancel 同一实际映像拥有的公开 SPI，再转发给该后端；不会用旧偏移读取源码连接对象。原包回退继续执行 UUID、代码字节和实例尺寸检查。构建时按固定 Git 提交验证原包连接参考源，其他仍共享的对象布局继续校验工作区文件，未解除共享对象布局保护。

直接源码 API、正常兼容库和损坏旧回退 UUID 的兼容库三种路径，每种均通过 8 个并发线程实际观察取消前后的状态，以及 32 轮真实异步取消、独立可修改/释放的字符串、连接释放后字符串存活检查。原包路径的 32 次回归和损坏 UUID 拒绝仍通过；160 个 rich-error 对象案例也通过。六组件目录已按新的 libxpc 重新构建，既有三组件联合回归、源码 kernel、responsibility 和 sandbox 调用层回归均通过。见 `artifacts/xpc-connection-source.json` 与 `artifacts/xpc-connection-native-analysis.json`。

补齐连接查询后，原版 Xcode 的 -showsdks 曾停在 `xpc_service_kickstart_with_flags`。下面的源码服务启动实现已越过该导出；完整 XPC 服务管理、Sandbox 策略、消息签名验证和完整项目构建/归档/签名仍未通过。

```bash
python3 scripts/build-libxpc-source.py
python3 scripts/build-launchd-source.py
python3 scripts/build-libsystem-kernel-source.py
python3 scripts/build-quarantine-source.py
python3 scripts/build-sandbox-source.py
bash scripts/test-xpc-connection-source.sh
python3 scripts/analyze-xpc-connection-native.py
python3 scripts/probe-full-native-xcode.py --source-runtime --source-kernel --source-quarantine --source-sandbox
```

Darling libxpc 的 `service_create/create_from_specifier/get_rendezvous_token/kickstart/kickstart_with_flags` 现有真实源码实现。对象保存名称、域、handle 和拥有引用的 dispatch queue，空名称生成 UUID，释放时清理资源。按原版 Intel libxpc 的实际 ABI，启动返回 int 错误；请求采用 subsystem 2、routine 702 和 `type/handle/name/unidomain/suspended/kill/unthrottle` 字段。没有沿用原版的私有对象偏移。原版 DVT 和 launchd 调用点的只读分析还确认：已有活动进程且不要求 kill 时，返回原 PID，不改变其暂停状态。

源码 launchd 接收真实 Mach audit 身份，只授权 root；支持受管理的 system 域任务，并查找现存 PID XPC 域。终止重启实际发送 SIGKILL，等原有 NOTE_EXIT/wait4 流程回收旧进程，再通过 job_dispatch/job_start 创建新进程并完成回复，不阻塞 launchd 事件循环。暂停标志进入现有 POSIX_SPAWN_START_SUSPENDED 后端。真实 launchctl 载入但未启动的任务、重复启动、连续 8 次重启均通过，验证旧 PID 已退出、新 PID 与任务记录一致；冷启动和重启暂停均核对实际 Mach suspend_count=1、未进入用户代码、task_resume 后开始执行。现有后端的该暂停状态不能用 SIGCONT 恢复，这一差异尚未修复。

测试同时覆盖 128 次 UUID/对象生命周期、自定义 queue 所有权、实际 API 与 xpc_release 属于同一后端、真实内核 audit 拒绝非 PID 1 的伪造回复、非 root 请求伪造字典身份仍被拒绝、畸形字段、未知 routine、缺失任务，以及原包 launchd 的真实接收超时。三组件和六组件服务测试通过，连接查询/旧兼容层保护、共享内存、退出统计、源码 kernel、responsibility 和 sandbox 既有回归重新通过。原有 630 个 libxpc 导出及 112 个 launch reexport 保留，新增两个导出后为 639 个。见 `artifacts/xpc-service-source.json`、`artifacts/xpc-service-native-analysis.json`、`artifacts/xpc-service-native-callers.json`。

**这不是完整 XPC 服务管理。** user/login/gui/rendezvous-token 域目前明确返回 ENOTSUP，PID 域尚未做正向执行验证；attach、通知回调、可配置 service-instance、entitlement 授权仍未实现。启动回复只证明真实 fork 得到 PID，不能证明执行成功或服务完成 check-in。每个任务只保留一个未完成的重启回复，并发重启返回 EBUSY；调用方超时不会撤回已请求的重启。

```bash
python3 scripts/analyze-xpc-service-native.py
python3 scripts/analyze-xpc-service-callers.py
bash scripts/test-xpc-service-source.sh
python3 scripts/probe-full-native-xcode.py --source-runtime --source-kernel --source-quarantine --source-sandbox
```

LoggingSupport 的后续实验保存在 `runtime/logging-support-native/frameworks`，独立于上述 30 库配置。Darling 原有 OSLogEventStream/Base 只是通用转发空桩；原版缺失类继承 OSLogEventStreamBase，自身有 18 个方法，基类有 20 个方法。`logging-support-native` 固定原版镜像 SHA，现已恢复原框架 78 个类的元数据及原指令，原版 Xcode 的加载错误从缺少 OSLogDeserializedEventStream 进到缺少 CADisplay。这只证明加载绑定继续推进，尚未验证事件解码、过滤、回调或日志数据源行为，没有加入空的替代类。见 `artifacts/logging-stream-native-analysis.json` 与 `artifacts/logging-support-native-probe.json`。

```bash
python3 scripts/analyze-logging-stream-native.py
python3 scripts/rebuild-c-cache-image.py --target logging-support-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/probe-logging-support-native.py
```

`runtime/quartzcore-native` 现保存追加原版 QuartzCore 的独立实验，保留原来的源码 CARenderServer 实验目录。原版 CADisplay 有 88 个实例方法和 5 个类方法；Xcode 的实际引用位于 DVTInstrumentsFoundation 的显示信息收集函数。新路径重建原版 QuartzCore 的 145 个类，并补上所需 Symbolication 的 100 个类、CoreSymbolication 的 3 个类。Symbolication 的合并缓存引用按唯一公开 Swift 符号恢复，包括 UInt64、Logger 描述符及标准库/原版 Foundation 函数。没有为 CADisplay 加入空的替代类，也没有把原版对象的私有字段偏移写进新的兼容对象。

原版 CADisplayMode 现已实际执行 490 组模式值测试：两种工厂入口、14 位宽高字段、16.16 刷新率编码、可变刷新标志、hash/相等性、16 字节序列化数据及独立可变副本均通过。测试核对类与工厂方法来自实际重建的 QuartzCore，再通过接口读取结果；未直接读取对象私有字段。这只验证选定的模式值 API，没有验证 CADisplay 的显示器枚举、全部模式/控制接口、渲染、GPU 或真实显示服务。Symbolication 的符号化/内存统计和其 Swift API 也未执行验证。见 `artifacts/ca-display-native-values.json`、`artifacts/ca-display-native-analysis.json`、`artifacts/ca-display-dvt-callers.json`。

新框架需要的 62 项 CoreVideo/CoreGraphics/CoreImage/ImageIO CFString 导入复用现有常量兼容库，并按原版对象逐项核对指针、CFString 类型和文本。`kCGLineWidthHairline` 则是 8 字节 double；已核对原版位模式及三处 QuartzCore 浮点比较调用。两个 CIFormat 常量按原版四字节值和 SDK 的 `typedef int CIFormat` 提供。兼容库当前共 143 个 CFString 和 6 个异型标识符；旧 Foundation 与六源码组件/原版 Foundation 下的类型、值、独立复制及标量位模式测试均通过。这些数据导出没有新增颜色转换、图像解码、像素缓冲区或绘图能力。见 `artifacts/quartzcore-native-constants.json`、`artifacts/cg-hairline-native-analysis.json`、`artifacts/coreimage-format-native-analysis.json`。

静态检查现在可选择实际使用的私有 Darling 目录，并保留同一文件经符号链接加载的别名；例如 CoreData 的 libsqlite3.dylib 实际选中 libsqlite3.0.dylib，其 sqlite3_free 导出不再被误报缺失。QuartzCore 的依赖图检查覆盖 217 个镜像：缺失强依赖镜像为 0、缺失弱依赖镜像为 40。传统绑定检查的 124198 个槽中，没有未解析的强即时绑定，仍有 889 个强延迟绑定、174 个弱即时绑定及 78 个弱延迟绑定未解析。另检查 15 个镜像的 3676 项 chained import 表，未发现未解析候选；12 项特殊查找序号没有审计，也没有逐条遍历指针链来证明每项记录的实际使用。这些都是静态名称检查，不代表 ABI、初始化或完整运行通过。见 `artifacts/quartzcore-native-dependency-inventory.json`、`artifacts/quartzcore-native-symbol-audit.json` 和 `artifacts/quartzcore-native-chained-import-audit.json`。

原版 Xcode 在该路径下已越过 CADisplay 和后续数据绑定，当前缺少 `_dyld_get_dlopen_image_header`，仍返回 255。该接口需返回真实 dlopen 句柄所属镜像的 Mach-O 头，并处理调用方/主程序及无效句柄；[Apple 开源实现](https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldAPIs.cpp)与本地固定版本已核对。Darling 旧加载器和 libdyld 目前都没有此接口，后续需在其源码边界接通真实句柄登记和加载生命周期。见 `artifacts/dyld-dlopen-header-source-analysis.json`。原版 xcodebuild 本体和默认 Darling 组件未改动，完整 SDK 列举、项目构建、归档及签名仍未完成。

```bash
python3 scripts/analyze-ca-display-native.py
python3 scripts/analyze-ca-display-callers.py
python3 scripts/prepare-quartzcore-native-constants.py
bash scripts/test-native-string-constants.sh
python3 scripts/test-quartzcore-native-constants.py
python3 scripts/rebuild-c-cache-image.py --target quartzcore-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/rebuild-c-cache-image.py --target symbolication-native --analyze-code --lazy-functions --modern-adapter --experimental-swift --repair-swift-relative
python3 scripts/rebuild-c-cache-image.py --target core-symbolication-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/probe-logging-support-native.py --native-quartzcore
python3 scripts/test-ca-display-native.py
python3 scripts/test-quartzcore-native-xcode-version.py
python3 scripts/analyze-dyld-dlopen-header.py
python3 scripts/record-quartzcore-native-progress.py
```

## 源码 libdyld 与 MobileAsset 查询客户端（2026-10-16）

`scripts/build-libdyld-source.py` 编译 Darling libdyld 的完整 28 个源文件，保留原有 180 个导出，并增加 `_dyld_get_dlopen_image_header`。它使用现有递归加载器锁、真实模块注册表及匹配源码的 C++ `machHeader()` 接口，不猜测 opaque handle 的私有字段，也不扫描文件名。实际测试覆盖无导出库、重导出库、多引用计数、同名模块、真实卸载失效、`RTLD_SELF`、主程序、无效 handle、错误状态保留和八线程的 512 次加载/查询/关闭循环；加载器快照、线程局部存储、原版 QuartzCore 的 490 组模式值操作和原版 Xcode 版本查询也通过。

这里重新编译的是完整 **libdyld 库**，主加载器 `/usr/lib/dyld` 仍是固定版本的发行包二进制。启动器检查其 SHA256 及源码接口 ABI，拒绝错误加载器或覆盖层替换。这条路径仅验证了该 Darling dyld2；没有完整重建主加载器，也未支持 dyld3 或其他加载器版本。

`scripts/build-mobileasset-source.py` 编译完整 14 文件 MobileAsset framework，保留原有 75 个导出，共 82 个导出。实现直接位于 `vendor/darling/src/private-frameworks/MobileAsset/src/Pallas.m`，覆盖 DVT 使用的五项客户端操作：enabled 查询/设置、audience 查询/设置、URL 设置，以及原有默认参数包装和内部别名。它们通过真实命名 XPC 服务 `com.apple.mobileassetd.v2` 发送动作码 32/33/20/10/9。enabled 查询分别处理 signed 64-bit `Result` 和布尔输出；audience 查询返回非持有字符串，服务错误返回 nil；URL 参数必须是 `NSURL`，空值设置 `serverOverrideClear`，错误类型返回 5。服务不存在时保留失败语义。

在旧版与原版 Foundation 配置下，跨进程协议测试各通过 174 个真实请求，其中各有 128 个并发请求，合计 348 个请求。测试包含启用/禁用、8 位布尔输入归一化、非零及超过 32 位的错误码、UTF-8 字符串和 autorelease 生命周期、nil/错误类型、URL 清除与默认参数。真实服务端断开后的一次重试成功和连续两次失败后停止也已通过。正向响应来自独立测试进程，经真实 Mach/XPC 传输；**这不证明已经运行 Apple mobileassetd**。客户端每次创建连接，尚未实现原版 manager 的持久缓存；首次 lookup/activation 竞态仍待补齐。资产目录、下载和安装服务没有实现，其他旧接口仍有占位代码。

该组合使用七个源码运行时组件，额外通过单次调用的 `DYLD_FRAMEWORK_PATH` 选择源码 MobileAsset，不修改发行包默认 framework。原版 `xcodebuild -version` 通过；`-showsdks` 已越过五项 Pallas 接口，下一处是 AppleSystemInfo。后续原版 ASI 实验见下节。

相关构建、执行和证据核验入口：

```bash
python3 scripts/build-libdyld-source.py
python3 scripts/test-libdyld-source.py
# SDK probe 当前预期退出 1；日志中的原版 xcodebuild 退出 255。
python3 scripts/probe-logging-support-native.py --native-quartzcore --source-dyld
python3 scripts/test-libdyld-source-regressions.py
python3 scripts/record-libdyld-source-progress.py
python3 scripts/analyze-mobileasset-xpc-native.py
python3 scripts/analyze-mobileasset-pallas-native.py
python3 scripts/build-mobileasset-source.py
python3 scripts/test-mobileasset-source.py
python3 scripts/analyze-mobileasset-dvt-callers.py
python3 scripts/probe-logging-support-native.py --native-quartzcore --source-dyld --source-mobileasset
python3 scripts/test-quartzcore-native-xcode-version.py --source-dyld --source-mobileasset
python3 scripts/record-mobileasset-source-progress.py
```

MobileAsset 阶段汇总为 `artifacts/mobileasset-source-progress.json`；源码补丁为 `artifacts/darling-libdyld-dlopen-header.patch` 和 `artifacts/darling-mobileasset-pallas.patch`，均已反向应用检查。

## 原版 Intel AppleSystemInfo 实验

`apple-system-info-native` 目标恢复原版完整 C framework 的 29 个导出，分析 43 个函数，保留原版 CPU 描述逻辑；只修复缓存指针、导入和重定位，没有加入新的 CPU 描述 hook 或 ASI 源码函数。原版资源包一并放入项目内的独立 framework。Darling 默认 ASI 二进制及原版 Xcode 保持原哈希。

实际执行覆盖 bundle 标识与本地化资源查找、25 组 CPU 数量/频率/字符串输入、10 组当前 CPU 格式标志、非持有返回值跨 autorelease pool 保留，以及 CopyCurrent 与原版底层接口的组合结果。100 MHz 和 500 MHz 输出有精确数值检查。Intel 路径使用 `Intel2xCPUFormat` 和内嵌 `2 x %@` 回退，不能套用旧版 PowerPC 的 `Dual %@` 资源预期。`ASI_CopyCPUKind` 接受缩写参数；CopyCurrent 也不是 format=1 的简单包装。

**硬件信息兼容尚不完整。** 当前 GHz 数字格式化路径会丢失频率部分；CPU-kind registry 查询缺少平台信息，当前描述使用原版 `Unknown` 回退。观测到 guest 的 CPU 数量标量为 1、频率标量为 2400000，实际硬件身份及频率单位正确性没有得到验证。这些限制记录在执行报告中，不能据此声称所有 29 个接口都已兼容。

```bash
python3 scripts/rebuild-c-cache-image.py --target apple-system-info-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/stage-apple-system-info-native.py
python3 scripts/analyze-apple-system-info-native.py
python3 scripts/test-apple-system-info-native.py
# 当前预期退出 1，原版 xcodebuild 在下一项 Security 接口处退出 255。
python3 scripts/probe-logging-support-native.py --native-quartzcore --source-dyld --source-mobileasset --native-systeminfo
python3 scripts/test-quartzcore-native-xcode-version.py --source-dyld --source-mobileasset --native-systeminfo
python3 scripts/record-apple-system-info-native-progress.py
```

当前汇总为 `artifacts/apple-system-info-native-progress.json`。原版 `-version` 通过；`-showsdks` 已越过 ASI 的导入缺口，下一处为 `SecPolicyCreateAppleExternalDeveloperOptionalExpiry`。证书策略需要保留实际对象、Apple 根约束、证书链/OID/EKU、撤销、密钥强度及有效期语义。完整 SDK 列举、Xcode/Unity/CocoaPods 工程构建、归档、签名和导出仍未通过。

## Security 策略构造与 pthread yield 导出

`vendor/darling/src/external/security/OSX/sec/Security/SecPolicyExternalDeveloper.c` 加入了 Apple 上游的完整可选有效期策略构造函数及 11 个辅助函数，函数体与固定版本 `db15acbe6a7f257a859ad9a3bb86097bfe0679d9` 逐项核对不变，并加入 Darling 的 CMake 和私有头文件。源码对应[Apple 原版实现](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/OSX/sec/Security/SecPolicy.c#L4082)。该组件使用现有 `SecPolicyCreate` 工厂和 CoreFoundation 选项构造真实对象，不访问私有对象字段。

这里编译的是选定的策略组件，**没有完整重建 Security.framework**。独立 staged Security 保留原有 4147 个导出及全部指令，仅增加新构造函数的 reexport 和已有隐藏 `SecPolicyGetOptions` 的导出可见性，后者用于真实选项检查。发行包 Security、原始 libSystem、已有 libSystem stage、原版 Xcode 和七个源码运行时组件的二进制保持原哈希。

构造函数 true/false 路径分别有 18/15 项选项，差异为有效期、黑名单和灰名单检查；其余 Apple 根、三张证书链、两个中间标记、九个叶标记、四个 EKU、撤销及 RSA/EC 密钥强度约束保留。相较旧策略，现代构造增加 UnparseableExtension、DuplicateExtension 和 Swift Package Registry 叶标记。旧版/原版 Foundation 及追加 yield 后的组合配置均通过真实对象、字段类型/值、所有权、变更隔离和每配置 128 个并发对象的检查。真实 DER 证书能够解析，新策略能进入现有 `SecTrust` 容器；**尚未验证证书链的信任结果及旧 trust 后端对所有现代检查项的执行**。

`pthread_yield_np` 已有实现位于 `scripts/foundation-libc-compat.c`，委托真实 `sched_yield`。新增的独立 libSystem 只转发这一项名称，不转发整个 helper 命名空间。已有 libSystem 和 helper 均不修改；helper 没有初始化器，依赖仅为 libSystem。源码路径为 libpthread 的 `sched_yield` → 所选 kernel 的 `swtch_pri_impl` → Linux `sched_yield`。项目内解包的 strace 确认主线程两条标记之间恰有 256 次成功的 Linux 调度调用，八个工作线程另外执行 1024 次调用；没有安装宿主机软件包或内核模块。

```bash
python3 scripts/build-security-policy-source.py
python3 scripts/analyze-security-policy-native.py
python3 scripts/test-security-policy-source.py
# 当前预期退出 1；原版 xcodebuild 已越过策略接口，下一处是 pthread yield。
python3 scripts/probe-logging-support-native.py --native-quartzcore --source-dyld --source-mobileasset --native-systeminfo --source-security-policy
python3 scripts/stage-pthread-yield-export.py
# 测试需要 runtime/tools/strace/usr/bin/strace；只在项目内解包使用。
python3 scripts/test-pthread-yield-export.py
# 当前预期退出 1；原版 xcodebuild 下一处是 Swift UTI URL 扩展。
python3 scripts/probe-logging-support-native.py --native-quartzcore --source-dyld --source-mobileasset --native-systeminfo --source-security-policy --pthread-yield-export
python3 scripts/test-security-yield-integration.py
python3 scripts/record-security-yield-progress.py
```

当前汇总为 `artifacts/security-yield-progress.json`，源码补丁为 `artifacts/darling-security-external-developer-policy.patch`，已做反向应用检查。组合配置的真实加载器快照、策略对象及原版 `-version` 回归通过。`-showsdks` 停在 `_$s10Foundation3URLV22UniformTypeIdentifiersE22appendingPathExtension3forAcD6UTTypeV_tF`；原版 Swift overlay 的代码在本地缓存中，但当前配置尚未恢复 UTI framework/overlay 的一致运行时。完整工程构建、归档、签名和导出目标保持未完成。

## 原版 UTI 配套恢复与运行时入口

独立目录 `runtime/uniform-type-identifiers-native` 保存原版 Intel UniformTypeIdentifiers 的 267 个导出、5 个类，以及 Swift overlay 的 627 个导出。缓存合并的十项 C++ RTTI/类型名引用按原版公开符号恢复，没有另造 UTType 对象布局。原版 framework 与 overlay 一起选择，原先以 String 存储的旧 Swift 替代实现没有被当成原版 ABI 使用。

`runtime/uti-runtime-support` 的 `backtrace_async` 入口函数体与固定 Apple Libc 提交 `71bbe350ab79eef58113991d817ccc6165061a64` 相同，使用此前的原版异步栈遍历器与已验证的 x86_64 后端适配。普通线程实际调用地址、容量 0–64、输出边界、空 task-id 输出及四线程检查通过；64 个实际 Swift 异步任务的任务 ID 和有界帧检查也通过。这里编译的是独立源码组件，未完整重建 libc/objc4。

原版 `libsystem_featureflags` 的两项功能开关实现也已恢复。它的依赖不能在 libSystem 初始化前直接加载，否则会形成初始化循环；小型源码加载器在第一次调用时按真实符号和拥有映像检查加载原版实现。它不决定功能开关的值。直接原版入口与转发入口通过缺失配置域、false/true 默认值和四线程测试；已有配置域中的真实开关与守护进程交互尚未验证。两个源码 helper 均没有初始化器，依赖仅为 libSystem；独立 libSystem 只按名称重导出三项新增入口，保留原有代码与导出。

组合环境中原版 `-version` 通过，`-showsdks` 已推进至 `_OBJC_CLASS_$_CALayerContext`。该类是 Cocotron AppKit/QuartzCore 的扩展，涉及其私有 layer context、纹理和渲染方法，与 Apple 的 CAContext 不同，不能仅替换类名。

这一阶段使用旧 objc4 的 UTI 类型与 URL 操作测试**未通过**。捕获的崩溃位于 Foundation 协议元数据处理调用 `_argInfo:` 的 `objc_msgSend`；原版 CoreFoundation 的短方法签名工厂会创建混淆后的 tagged NSMethodSignature，而该组合禁用了 tagged dispatch。仅重新启用旧运行时 tagged 支持的独立诊断会超时，也不是可用修复。历史证据见 `artifacts/uti-native-blocker-analysis.json`。下一节的源码 objc4 已修复这处启动前崩溃，完整 UTI 测试仍受数据库服务阻塞。

```bash
python3 scripts/rebuild-c-cache-image.py --target uniform-type-identifiers-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/rebuild-c-cache-image.py --target swift-uniform-type-identifiers-native --analyze-code --lazy-functions --modern-adapter --experimental-swift --repair-swift-relative
python3 scripts/rebuild-c-cache-image.py --target system-featureflags-native --analyze-code --lazy-functions --modern-adapter
python3 scripts/stage-uniform-type-identifiers-native.py
python3 scripts/build-uti-runtime-support.py
# 当前预期失败：原版 -showsdks 仍缺 CALayerContext。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --version
python3 scripts/test-backtrace-async-native.py
python3 scripts/test-featureflags-native.py
python3 scripts/build-uniform-type-identifiers-native-fixture.py
# 当前预期失败：独立 UTI 功能测试在主函数之前崩溃。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --uti-fixture
python3 scripts/record-uti-native-progress.py
```

这些新目录仅由独立实验命令选择。默认运行时、前一阶段目录、Xcode 原始二进制保持不变；完整工程构建、归档、签名与导出仍未完成。

## 完整源码 objc4 与原版 LaunchServices 服务

这一步直接修改 Darling 的 objc4 源码。旧 `objc_object` 把 ISA 声明成对齐的 `isa_t` 成员，Clang 在生成 C++ `object_getClass` 等路径时会因此消除最低位 tagged pointer 检查。源码回移 Apple objc4 `fb265098298302243cd7eeaa1f63f0ba7786dd9a` 的 ISA 字节存储及访问器，并更新原有 ISA 访问。编译器输出对比确认：对象仍为 8 字节，class 仍为 40 字节，superclass/cache/bits 偏移仍为 8/16/32；只去掉 C++ 对对象指针天然对齐的假设。没有修改原版 NSMethodSignature 或猜测其私有对象字段。

`build-objc-source.py` 编译 CMake 声明的全部 43 个源文件，保留发行包全部 770 个导出。解除旧隐藏名单对 `__IncompleteProtocol` 的隐藏，以保留发行包原有的 class/metaclass 导出。独立构建使用 Apple `ld-classic`，确认 `__objc_init_func` 保留给 libobjc 的早期初始化流程；现代 ld 曾未按原有选项重命名初始化节，实际启动报 mutex 错误，因此该构建明确检查节名称。发行包默认 libobjc 没有覆盖。

真实执行验证包括：

- 同一个程序在发行包运行时失败，在源码运行时通过 19 组 basic/extended/最大 tag 的类查询、消息派发、强弱引用及普通堆对象检查。
- 原版 CoreFoundation 的七种方法签名通过，并确认短签名确实是 tagged 对象。原版 NSInvocation 实际完成整数、double 和 24 字节结构体返回值调用。
- 组合路径通过 47 镜像的真实加载器快照及 Mach 权利检查，以及完整证书策略选项、生命周期和 128 个并发对象回归。证书链验证仍未建立。
- 原版 Xcode `-version` 通过；`-showsdks` 仍因 Cocotron AppKit 所需的 CALayerContext 缺失而退出 255。

UTI 不再停在启动前的方法签名崩溃。原版 plain-text 标识和首选 txt 扩展名已执行；实际 URL 扩展调用进入 NSURL/UTType 的符合关系查询，再进入 LaunchServices 数据库与 NSXPC 同步等待。**没有输出正确 URL 的成功证据，完整 UTI 测试仍失败。** 最新真实等待栈为 `artifacts/uti-source-objc-current-live-stack.json`。

`probe-native-lsd.py` 复用恢复系统中的原版 Intel `/usr/libexec/lsd`，保持二进制哈希及系统 daemon 的 13 个 MachServices 定义。只在一次独立 Darling 会话中用工作区路径加载任务，并传入实验框架/库环境。实际 launchctl load 成功，但 daemon 在启动中退出 139；探针确认没有运行中的 PID 后结束，不再让客户端反复触发崩溃重启。

已保存原版 daemon 的 core、当时运行时快照和符号化调用链：`_LSServerMain` → `currentSchemaVersion` → libTrace `_os_log_impl` → `objc_msgSend`。日志格式器、ASL/CF 对象 ABI 或对象生命周期的根因仍待核对，未关闭日志，也未伪造数据库回复。`archive-native-lsd-cores.py` 只清理 ELF 命令行明确匹配这一临时 lsd 的重复 core，保留一个完整现场；其他诊断 core 不受影响。

```bash
python3 scripts/build-objc-source.py
python3 scripts/analyze-objc-source-layout.py
python3 scripts/test-objc-source-tagged.py
# 当前预期失败：仍缺 CALayerContext。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --source-objc
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --source-objc --version
python3 scripts/test-objc-source-signatures.py
python3 scripts/test-objc-source-integration.py
python3 scripts/build-uniform-type-identifiers-native-fixture.py
# 当前预期失败：进入原版 URL 代码后等待数据库回复。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --source-objc --uti-fixture --timeout 20
# 当前预期失败：原版 lsd 启动崩溃，没有存活 PID。
python3 scripts/probe-native-lsd.py
python3 scripts/archive-native-lsd-cores.py
python3 scripts/record-objc-source-progress.py
```

当前源码补丁为 `artifacts/darling-objc-source-tagged.patch`，汇总证据为 `artifacts/objc-source-progress.json`。源码 objc4 只由这条实验路径选择；完整 Objective-C 运行时兼容性、现有外部类枚举适配器向源码运行时的迁移、AppKit/QuartzCore 兼容、数据库服务及完整构建/归档/签名仍未完成。


## 源码 libtrace 修复与原版目录服务

Darling libtrace 的 `%{public}` / `%{private}` 处理原先移动了格式字符串起点，却继续使用旧下标，导致后续参数解码错误。现在直接修改该源码中的解析下标，并检查编码记录边界、标量符号扩展和字符串终止容量。完整编译 CMake 列出的 8 个源文件，保留原来的 142 个导出；只在实验库路径选择新库。原版 Xcode 和默认打包的 libTrace 均未改动。

21 组 Clang 实际编码的日志、全部前缀截断的保护页检查、1023/1024/1025/4096 字符边界通过。`DARLING_OS_LOG_STDERR=1` 是可选诊断开关，通过真实 ASL 客户端输出；已核验实际记录 `LIBTRACE_ASL_E2E -77`，并在原版 lsd 中看到 schema version 20971545 的启动记录。其他现有日志活动、插件/格式化桩和持久统一日志投递未因此补全。

缺失的 `__user_local_dirname` 与 `rootless_mkdir_datavault` 使用两个有类型的延迟转接入口，调用已有的原版 Intel 实现，通过私有 libSystem 副本逐个再导出。没有合成用户 UUID 或路径，也没有用普通 mkdir 代替受保护目录创建。15 组用户路径边界/错误码对照通过；4 组 data-vault 错误和文件系统副作用对照也通过。正常新建受保护目录仍返回 `ENOPOLICY`，并留下未受保护的目录；没有保护能力成功的结论。

接入这些入口后，原版 lsd 能进入 `LSDatabaseBuilder` 和实际 store 加载路径，但数据目录 URL 为空，随后在 `stringByAppendingString:` 抛异常。原版 `_dirhelper` 能计算用户路径，初始化目录则返回 `ENOENT`。已另外暂存原版 `/usr/libexec/dirhelper` 和 `com.apple.bsd.dirhelper` Mach 服务配置；任务 load 成功，程序因缺 `_os_log_simple` 退出，服务及目录初始化尚未通过。

```bash
python3 scripts/build-libtrace-source.py
python3 scripts/test-libtrace-source.py
python3 scripts/stage-user-local-dir-export.py
python3 scripts/test-user-local-dir-export.py
python3 scripts/analyze-rootless-datavault-native.py
python3 scripts/stage-rootless-datavault-export.py
python3 scripts/test-rootless-datavault-export.py

# 当前预期失败：SDK 列举缺 CALayerContext。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --source-objc --source-libtrace --user-local-dir-export --rootless-datavault-export
# 通过：原版版本命令、49 个映像的加载器快照和 128 个策略对象。
python3 scripts/probe-uniform-type-identifiers-native.py --runtime-support --source-objc --source-libtrace --user-local-dir-export --rootless-datavault-export --version
python3 scripts/test-objc-source-integration.py --source-libtrace --user-local-dir-export --rootless-datavault-export
# 当前预期失败：lsd 数据目录异常；dirhelper 缺 _os_log_simple。
python3 scripts/probe-native-lsd.py --source-libtrace --user-local-dir-export --rootless-datavault-export
python3 scripts/probe-native-dirhelper.py
python3 scripts/record-libtrace-directory-progress.py
```

当前源码补丁为 `artifacts/darling-libtrace-parser.patch`，汇总证据为 `artifacts/libtrace-directory-progress.json`。实际实现仍是 Darling 源码修复、原版库和外部转接层的组合，尚未统一成完整 Darling 源码构建。所有服务实验在独立会话运行并退出；未安装宿主服务或内核模块。


## 简单日志源码与类型化分配入口

`_os_log_simple` 已从 Apple libplatform 的固定提交 `2512ffd8bb5c6caff3c8ea83331ab8a0adc820c3` 移植到 Darling 源码目录。保留上游格式化、时间/进程信息、UUID/映像偏移、2048 字节线格式及解析函数体，发送函数只增加可选 stderr 诊断。Darling 侧使用真实 Unix 数据报 socket，并处理 fork 后继承的连接锁；线程 ID 调用实际 pthread 接口。作为独立源码组件编译，通过私有 libSystem 的 8 个指定导出选择，未完整重建 platform，也未改动其 CMake 默认目标。

实测收发 104 个数据报，覆盖 96 条并发记录、并发日志期间 fork 的子进程、UTF-8 可变参数、线程/进程 ID、输入 UUID、普通映像及共享缓存偏移、2048 字节边界、保护页上的全部截断前缀。没有接收端时返回实际 `EBADF`；显式 launchd 重连后实际发送成功。默认目标是系统日志 socket；`DARLING_SIMPLE_LOG_SOCKET` 可指定诊断接收端，`DARLING_OS_LOG_STDERR=1` 可同时显示消息。没有建立 logd 或持久统一日志存储，也未证明所有早期启动、异步信号及 fork/exec 情况都可用。

`malloc_type_malloc` 等 13 个入口使用 Apple libmalloc 提交 `c49dafa25f1efe8607701ae6014a663ad2ee437f` 的完整、未改动 `malloc_type_stubs.c`。这是上游提供的普通分配器回退层：实际调用 malloc/calloc/realloc/free、对齐分配和真实 zone API；没有 xzone 类型隔离。全部 13 个入口通过默认/独立 zone、对齐、清零、溢出失败、realloc 失败保留旧内存、跨入口释放及 256 个并发分配生命周期测试。没有重建完整 malloc。

原版 `rootless_mkdir_nounlink` 使用另一个有类型的延迟转接入口，仍执行原版 Sandbox 代码。静态核验确认三个参数及 `SF_NOUNLINK=0x100000`，四组调用的返回值、errno 和文件系统副作用与直接调用一致。新建保护目录依然返回 `ENOPOLICY`，没有新增保护策略或保护成功的结论。

原版 dirhelper 已越过 `_os_log_simple`、`malloc_type_malloc` 和 `rootless_mkdir_nounlink` 的加载错误，当前缺 `sandbox_container_path_for_audit_token`。最新组合的原版 Xcode 版本命令、52 个映像的真实加载器快照和 128 个证书策略对象通过。目录服务、完整数据库/UTI 客户端及完整 xcodebuild 仍不成功。

本阶段入口：`scripts/build-os-log-simple-source.py`、`scripts/test-os-log-simple-source.py`、`scripts/build-typed-malloc-source.py`、`scripts/test-typed-malloc-source.py`、`scripts/stage-rootless-nounlink-export.py`、`scripts/test-rootless-nounlink-export.py`。原版服务探针可用 `scripts/probe-native-dirhelper.py --source-simple-log --typed-malloc --nounlink-export` 重现当前失败。核验与后续工作保存在 `artifacts/directory-runtime-progress.json`；源码补丁为 `artifacts/darling-platform-simple-log.patch` 和 `artifacts/darling-malloc-type-fallback.patch`。


## 原版目录帮助器启动与用户目录创建

新增 Darling 源码 `src/sandbox/container.c`，按原版 Intel 指令传递 by-value 的 32 字节 audit token，将 PID、PID version、输出缓冲区、容量和标志 1 传入真实 `Sandbox` MAC operation 4。编译结果与原版 wrapper 的栈/寄存器参数位置已对照；自身 task token 的 PID/UID/GID 字段及 12 组原版/源码/实际 MAC 错误对照通过。当前策略不存在，正确保留 `ENOPOLICY`；没有合成 container path。PID version 当前为 0，其他进程身份、PID 复用和成功容器查询未验证。此文件仍按独立组件编译，未完整重建 Sandbox。

此前 overlay 上层误建了 `/var` 目录，遮住基础根文件系统的 `/var -> private/var`，因此连基础层的 `/var/root` 也不可见。`scripts/repair-overlay-var.py` 在会话锁下合并无冲突文件、保留完整原上层目录备份，再恢复符号链接；仅修改项目私有 guest。`scripts/prepare-native-directory-root.py` 创建原版目录服务所需的 `/var/folders` 基目录并验证布局。原版 daemon 此后保持 PID，原版目录库实际创建 `0/`、`T/`、`C/` 三个目录。这里只证明 daemon 启动及原版库的目录创建，未证明创建一定经过跨进程 MIG 请求。

已将恢复系统中完整的 `CoreTypes.bundle` 原样导入私有 overlay，逐文件核对 272 个文件/链接以及 761 个 exported、440 个 imported 声明。合并启动原版 dirhelper/lsd 后，lsd 能继续到应用目录扫描，并写出 `SystemDataOnly-com.apple.LaunchServices-20971545-v2.csstore`。当前仍缺 `_sysdir_start_search_path_enumeration_private`；CoreTypes 注册也因元数据操作 EINVAL 失败。文件存在不代表数据库已正确反序列化或类型目录可用。

最新原版版本命令、53 映像的加载器快照和 128 个策略对象回归通过。默认环境的 Darwin/Python/Ruby、持久化、退出码和宿主隔离 smoke 也通过。全局文件所有权转换仍沿用 Darling 原有的“返回当前调用者 UID/GID、flags 清零”行为，目录保护及多用户权限未因此实现。

```bash
python3 scripts/build-sandbox-container-source.py
python3 scripts/test-sandbox-container-source.py
python3 scripts/analyze-sandbox-container-native.py
python3 scripts/prepare-native-directory-root.py
python3 scripts/stage-coretypes-resources.py
python3 scripts/probe-native-dirhelper.py --source-simple-log --typed-malloc --nounlink-export --sandbox-container
# 当前预期失败：lsd 在应用扫描时缺私有 sysdir 入口。
python3 scripts/probe-native-lsd.py --source-libtrace --user-local-dir-export --rootless-datavault-export --sandbox-container --with-dirhelper
python3 scripts/record-directory-services-progress.py
```

当前证据在 `artifacts/directory-services-progress.json`，源码补丁在 `artifacts/darling-sandbox-container-query.patch`，完整原上层 `/var` 备份位置记录在 `artifacts/overlay-var-repair.json`。完整 xcodebuild 构建、归档、签名、导出仍未完成。


## 配对的原版 sysdir 枚举与真实元数据请求

`runtime/sysdir-native-export` 通过三个指定再导出入口，成套调用同一原版 Intel DirHelper 的公共 starter、私有 starter 和 get-next。静态核验确认枚举状态为 32 位，两个 starter 使用同一函数体，公共入口过滤 `0x1ff0` domain 位、私有入口保留这些位。没有将原版状态交给旧 Darling 解码，也没有合成目录路径。

2,210 组对照通过，逐项核验 1,939 个返回路径、状态推进、顺序、终止和缓冲区边界；168 组公共/私有状态确实不同。原版目录帮助器仍能启动并初始化现有用户目录。原版 lsd 已越过私有枚举缺失，进入 remote placeholder 注册阶段，下一处缺失是 `container_query_create`。这不等于应用或类型目录已注册成功。

新增真实 Foundation 复现程序：传统 `NSFileManager` attributes 查询返回 14 项，但 `NSURLIsDirectoryKey` 与目录枚举失败。用私有进程中的 GDB 断点观察实际内核入口，捕获四组 getattrlistat 参数：

| 缓冲区容量 | options | commonattr | dirattr | fileattr | extended common |
| --- | --- | --- | --- | --- | --- |
| 930 | `0x25` | `0xd01f9e0d` | `0x5` | `0x1` | `0x240` |
| 962 | `0x25` | `0xd01fde0d` | `0x5` | `0x1` | `0x240` |
| 8 | `0x1` | `0x40000000` | 0 | 0 | 0 |
| 1084 | `0x29` | `0x8800000a` | 0 | 0 | 0 |

前两组请求包括文件类型、时间、权限、返回属性位图及扩展字段；最后一组请求完整路径和返回位图。现有共享 `getattrlist_generic.c` 仅支持少数 FinderInfo/objtag/目录项数/resource-fork 属性，遇到这些位就返回 EINVAL，尚未实现返回属性集与扩展 common 字段。当前阶段只观察和定位问题，未改动内核，也未通过填零或伪造支持位制造成功。

```bash
python3 scripts/stage-sysdir-native-export.py
python3 scripts/test-sysdir-native-export.py
python3 scripts/analyze-sysdir-native.py
python3 scripts/build-coretypes-resource-fixture.py
# 当前预期失败：真实 URL 属性与目录枚举未实现。
python3 scripts/probe-coretypes-resource-values.py
# 已捕获的 live 参数与当前源码拒绝条件对照。
python3 scripts/analyze-coretypes-getattr-requests.py
python3 scripts/record-sysdir-metadata-progress.py
```

后续需要在共享源码内实现真实文件属性、returned masks、extended common、Darwin 四字节对齐/变长引用偏移、短缓冲区规则和实际不支持错误，再验证原版 Foundation/LaunchServices。当前组合的版本命令、54 个映像的加载器快照与 128 个策略对象通过；完整 UTI、SDK 列举、工程构建、归档和签名仍未完成。证据入口为 `artifacts/sysdir-metadata-progress.json`。
