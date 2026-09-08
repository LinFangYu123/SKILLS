# 组播（Multicast / MCAST）项目简历描述（详细版）

> 来源：`项目SOW/` 下 31 份组播工作任务书，每份由独立 subagent 通读全文分析。代码量为任务书官方 LOC 数据（标注"折算"者为任务书给出的折算值），功能描述均取自任务书原文。

## 一、组播大规格与转发平面优化

### 1. 组播按需下发（不同板组播规格叠加）｜ 园区核心交换机 S10500V7 ｜ 4300 行（新开发）
- **背景**：大规格模式（`multicast replication-share enable`）下各接口板表项一致、均占用前缀资源，设备表项规格受单板规格限制，无法随板数扩展。
- **功能**：评审选定"流量法"按需下发——仅在流量入口板下发绑定复制资源，非入口板不占用前缀资源，实现整机表项规格为各板规格的叠加；流量切换后在新的入口板经未知组播上送触发表项下发。适配 PIM SM（注册 dummy 表项转正后按入口板绑定、SPT 切换在新板重下驱动）、PIM SSM（等流量到达再绑定复制资源）、PIM DM、IGMP Proxy；双向 PIM 不支持大规格故不涉及。新增命令 `[ ipv6 ] multicast forwarding-conversational-learning`（产品定制项 FwdConverLearn，非大规格模式可配但不生效并提示）；表项 ID 规格调整为各板表项规格之和，接口板启动上报规格（参考 MFIB_TOMAIN_BOARDINFO）、主控板累加放大并通知其他板，只增不减，新增显示各板表项 ID 规格/表项规格/已下发表项数；`display multicast forwarding-table`、`display system internal multicast capability` 增加规格与下发信息；全局口（聚合/VLAN/VSI/Tunnel）依附板难以确定，按评审统一走流量法。
- **难点**：全局口成员板不可精确获取；SSM 按需下发丢包窗口；表项 ID 规格动态化引入的板间时序与内存/老化遍历性能问题（新增挂接节点将需老化上报表项挂链）；模式切换时表项 ID 只增不减的约束。
- **代码量**：总 4300 行（新开发，C），整体难度较高，人力 3 人。

### 2. 大规模提升组播路由规格（复制资源复用）｜ Comware V9R1 ｜ 12500 行
- **背景**：组播复制资源规格（8k/16k）受硬件限制，原实现每条表项独立占用复制资源，相同出接口的表项重复消耗。
- **功能**：将出接口提取为独立"组播复制资源"先下驱动，表项以引用计数关联共享（key 为所有出接口索引求和），实现"N 条表项 + 1 条复制资源"；主控板计算 key、分配全局唯一 index 并同步接口板，接口板按主控 index/产品信息下驱动、出接口列表按本板最新表项自行计算；新增 IPMC_L3_CREATE/DESTROY/APPEND/REMOVE_REPLICATE、IPMC_L3_ENTRY_BIND_REPLICATE 等驱动命令字；覆盖三层路由口、VLAN/VSI/super-VLAN（三级 key）、MVPN MTI（含 data-group）、跨 VPN 表项合并、MUA/MUPE、双向 PIM（RP 表项不复用）等形态；功能开关经 IPMC_CONF_S 定制三种取值，主控从 DBM 读配置、接口板经 SYNC 同步，ISSU 升降级约束设计；新增 `display multicast outgoing-interface share info`、forwarding-table replicate 过滤、下驱动记录 rep-index 过滤、event-log、Simware 驱动桩（复制资源 index 树/前缀树校验）。
- **难点**：出接口索引求和 AVL key + 冲突链 + 唯一 index 二级树的数据结构设计；主备倒换非稳态下 index/产品信息/出接口三者不一致的断流问题（驱动校验 index 失败由平台重刷）；二层组播端口扩展时序（新增 MFIB_RT_EXT_L2PORTSLOT 消息，统一由主控板同步）；V9 用户态转发进程打包下驱动适配、IPv4/IPv6 双栈合并、切换复制资源不丢包。
- **代码量**：总 12500 行（移植约 5300、V9 适配约 5700），难度系数 1.5，整体难度/风险高。

### 3. 组播复制资源复用模式跨板优化及 FRR 完善｜ S10500V7 ｜ 7000 行（新开发）
- **背景**：大规格模式下表项入/出接口跨板时，出口板增删出接口触发复制资源新建/删除，硬件只能按入口板携带的单个复制资源索引查表，时序错位导致丢包/断流；另有 FRR 备份入接口为 VLAN/VSI 且同时作为出接口时表项维护不全、32K 表项下 VLAN 口 FRR 切换断流 20~60 秒两类遗留问题。
- **功能**：跨板两阶段确认机制——主控板创建复制资源后新增"创建完成"板间消息（MFIB_TOMAIN_REP_CREATED）等所有接口板回应，全部到齐再发"绑定"消息（MFIB_RT_BIND_REP）统一切换；删除采用"超时删除 + 确认"（MFIB_RT_DEL_REP），无引用资源挂待删除链定时老化、可复用。表项新增 uiNewRepIndex、扩展 uiOldRepIndex，复制资源新增 CREATING/DELETING 中间状态，主控板以 AVL 树维护表项依赖，处理创建中拔/插板、主备倒换、板插入平滑（先同步复制资源再同步表项）。FRR 备份一致性 8 个修改点：NSR 恢复备份入接口、倒换后 PIM ASSERT 修复、备份入接口兼作出接口的端口扩展与板间同步（PE 口/全局口/普通口分别处理）、VLAN 口与二层表项关联解除、板插入备份入接口同步、大规格与 FRR 资源复用适配。MFIB VLAN 二层端口扩展改两阶段异步分批（每批 32 表项，MCS 消息队列驱动），按最终状态抵消中间时序，VLAN 口 FRR 切换断流从 20~60 秒降至毫秒级。
- **代码量**：总 7000 行（新开发，C），30 个功能点，难度系数 1.706，4 人，难度/影响度/风险均高。

### 4. B70D064SP 特性同步到 V9 trunk——组播驱动接口适配｜ V9 trunk ｜ 6500 行（新开发6000 / 移植500，折算6180）
- **背景**：V9 转发进程/驱动进程分离，组播下驱动改为跨进程 TLV 消息；园区核心/SR88 产品要求由平台实现消息收发解析、还原为与 V7 一致的驱动接口，减少产品适配。
- **功能**：基于框架 LRPC 实现转发进程到驱动进程远程调用（LRPC_ClientCall 长连接 + 共享内存传参，避免消息拷贝），下驱动消息按 82 种一级 TLV 打包；驱动进程侧新增 LRPC 插件 liblrpcplug_mfib.so 实现多级 TLV 解析框架，还原 V7 形式驱动接口（IPv4 共 21 个、IPv6 共 18 个 "_Real" 接口），处理结果逐级回填 TLV；覆盖三层组播表项头/出接口/出端口增删、VRF/接口使能、双向 PIM RP 及 DF、MTI 封装、RPF 失败报文、FRR 主备入接口流量检查、M-LAG 奇偶转发规则、复制资源复用、VXLAN 封装逃生、二层 IGMP/PIM Snooping、路由器端口、组播 VLAN、source-deny、报文上送（VXLAN L3VNI、DCI 隧道）及查询通知类接口；改进下驱动返回值机制（总返回值区分驱动是否处理 TLV）；simware9 新增组播驱动桩 libdrv_ipmc_simware.so 及 CLI 插件（TLV 解析调试、设置返回值、查看桩状态）。
- **难点**：多级 TLV 逐条解析与 V7 结构还原、表项与出接口一体/分离两种失败重刷模型；量大频高的下驱动采用长连接 + 共享内存 + 批量打包降低开销。
- **代码量**：总 6500 行（新开发 6000 / 移植 500，折算 6180），难度系数 1.2375，3 人。

### 5. B70D064SP 特性同步到 V9 trunk——组播大规格优化等｜ V9 trunk ｜ 11700 行（新开发5800 / 移植5900，折算6900）
- **功能**：需求 1.1 复制资源复用跨板优化（4 类板间消息、CREATING/DELETING 中间状态、创建中/待删除板位图与各板确认机制、超时 30s/60s、表项依赖 AVL 临时树、适配主备倒换/插拔板/按需下发）；需求 1.2 B70 FRR 完善（备份入接口为 VLAN 虚接口且兼作出接口、二层端口变化、全局口、NSR 恢复、PIM ASSERT、大规格资源复用适配）；需求 1.3 MFIB 性能优化（VLAN 二层端口扩展异步分批，消除 FRR 断流 20~60s）；需求 2 B70/B75 MSDP NSR——配置/运行数据（peer 状态机、SA 表项、VPN/接口/路由策略/MBGP 事件）实时批备，V9 TCP NSR 纯新开发：基于 Linux TCP Repair（TCP_REPAIR_QUEUE/TCP_QUEUE_SEQ 等），备份接收报文队列、应用层备份发送缓冲区与 RcvNxtPduSeq/SndPeerACK 序号、TCP_NSR_STANDBY/ACTIVE 选项实现 TCP 连接无缝迁移，处理 FIN/RST 拦截与 inpcb 迁移。
- **性能目标**：大规格表项下组播 FRR 切换丢包小于 200ms。
- **代码量**：总 11700 行（新开发 5800 / 移植 5900，折算 6900），整体难度高，3 人。

## 二、EVPN / VXLAN / M-LAG 组播

### 6. 组播补齐一期（B70 MULTICAST EVPN 一期 / 组播 VXLAN 基础特性补齐）｜ V9 trunk ｜ 88.2K 行（一期75.8K：移植65.2K / 新增10.6K）
- **背景**：V9 trunk 主线补齐 V7 B70 分支已商用的组播 VXLAN 基础特性，汇集 7 个来源需求（中国广电核心复制、腾讯手工 VXLAN 模型三层组播、NEC EVPN VXLAN 二层组播、北京地铁 11 号线 M-LAG、S5560X DRNI 场景 IGMP proxy、125G 设备 EVPN 组播 IPv6、DRNI 改名 M-LAG），一期保 CLI 功能，NETCONF/MIB 留二期。
- **功能**：MVXLAN 三层组播核心复制（`multicast-vpn vxlan` 按 VPN/公网实例创建 MVXLAN，ingress-replication/mdt 模式，Default/Data-Group 切换与 data-delay，每 data-group 独立 Mtunnel 口，PIM distributed-dr，SBD-IMET/SBD-SMET，经 BGP 6/10 类路由携带 PMSI Tunnel 属性，头端 Mtunnel 携带 L3VNI、尾端 MVXLAN_UPE 虚拟口解封装）；手工 VXLAN 模型三层组播（MFIB 扩展 Vxlan 端口，软转与硬件双支持）；VXLAN 下二层组播 IGMP PROXY（VSI 视图 igmp-snooping proxy enable，维护 EVPN 路由表，6/7/8 类路由，L2VPN 经 MCS_PROTOCOL_EVENT 交互）；DRNI/M-LAG 场景（虚拟源地址配置与故障切换、data-group 同步、防火墙快速切换、BGP AD-PATH）；L3VNI VSI 虚接口 IGMP proxy（IMET 发布、组成员维护、wrong-if、BGP SMET version/include/exclude 下发）；EVPN 组播 IPv6 地址族（MD/MRIB6/PIM6/MLD 适配、SSM、Anycast-RP、S-PMSI source-active）；DRNI→M-LAG 双关键字兼容；COMMIT 基础/增强与 URL 数据冲突检查；V9 通信适配（LIPC 字节序转换、MFIB 消息 TLV 化、驱动接口收敛为 DRV_MC_HandleMrouteChange、L2MFIB 由 CIOCTL 改 LIPC、epoll 回调重写）。
- **难点**：MFIB 移入转发进程独立线程后的消息框架重构；COMMIT 冲突检查需维护 URL 配置数据；涉及 MVXLAN/PIM/PIM6/MRIB/MRIB6/MFIB 主模块与 L2VPN/BGP 配合，难度与风险评级高。
- **代码量**：一期 75.8K 行（移植 65.2K / 新增 10.6K），与二期合并 88.2K，86 项功能点，6 人并行。

### 7. B70 MULTICAST EVPN 二期（V7V9 特性补齐专项）｜ V9 trunk ｜ 33700 行（移植20700 / 新开发13000）
- **功能**：非对称跨 VPN 组播路由互引（`multicast extranet select-rpf [l3-vni | vpn-instance]`，Mroute/Ipv4/Ipv6ExtranetSelectRpfs 表增加 SpecifyL3vni/SenderL3vni 列，对称/非对称 VPN 切换、平台层表项合并免驱动修改）；EVPN 三层组播 DCI 互通（MVXLAN IPv4 视图 `dci enable`，BGP 10 类路由发布组播源，L3VNI 映射，源/点播侧跨 DC 流量与源迁移）；3ED 组 DCI 三层组播（`multicast-vpn vxlan edge remote`，多 ED 转发设备选举与故障切换）；M-LAG DCI（`multicast-vpn vxlan m-lag local/remote`、`dci switch-delay`）；EVPN 二层组播 IGMP PROXY 及 ES 组播（forwarding-mode ip/mac、display igmp-snooping evpn-group、IGMPv3/MLDv2 exclude、ES TCN/DF/BDF 切换、non-DF 口 ACL 禁转）；igmp-snooping access-policy 放开；组播 trap；组播 FRR（`rpf-frr enable [policy]`、`multicast frr monitor cycle/wtr/mode`，备份入接口维护与下内核、MFIB ADJ/BFD 事件、分布式新架构、mofrr 独立线程流量检测）。
- **说明**：属 V7V9 特性补齐专项（与第 6 项一期同系列，NETCONF/MIB 在二期补齐）；进程级 HA M3 模型，MLAG/vSys 天然支持。
- **代码量**：总 33700 行（移植 20700 / 新开发 13000），难度系数 1.377，2 人。

### 8. VXLAN 三层组播核心复制支持 M-LAG（公网 ECMP）｜ 园区核心（5560X/6520X 等）｜ 1200 行（功能点合计）
- **功能**：尾端设备按 system number 奇偶规则加入/剪枝核心复制隧道（system number 1 加奇数剪偶数、2 反之，响应 DRNI_SYSEVENT_NUMBER_CHANGE）；peer-link down 时向奇偶组都发加入、恢复时仅本端奇偶组加入（DRNI_IFEVENT_IPP_DOWN/UP）；表项出接口不扩展 peer-link 口且软转不往 peer-link 转发防多包；依赖主线 `vxlan multicast-group member enable` 逃生 VLAN 命令与 pfDRV_MC_HandleVxlanMGrpMemChange 驱动接口，处理"先配 VLAN 后建表项/先建表项后配 VLAN"时序及逃生 VLAN 接口激活/删除/up/down 事件；覆盖头端/尾端私网 DR 故障、公网 DR 故障、peer-link 故障 MAD 单机、脑裂等场景；NETCONF（Mroute/Ipv4Interfaces 模型 VxlanMGrpMem 节点、XML2CLI、Candidate）。
- **难点**：实地址隧道在 ECMP 下因 PIM ASM 无 (S,G) RPT prune 产生多包，仅支持 M-LAG 虚地址方案；双活网关 PIM 邻居冲突/RP 学习失败（RFC 7761 二级地址覆盖致 Join/Prune 震荡、BSM RPF 失败），采用虚 IP 作 PIM 邻居主地址；基于 PIM RPF 引流原则分析头端 BUM 流量被奇偶规则丢弃问题，采用 peer-link 三层逃生 VLAN 方案。
- **代码量**：7 个功能点合计约 1200 行（C，全部新增），难度系数 1.27，用户态占比 70%。

### 9. 浪潮组播 VXLAN 核心复制支持 M-LAG｜ B70D064SP34XX（5560X/6520X）｜ 1900 行（功能点明细合计）
- **功能**：三层组播 VXLAN+M-LAG 新增 M-LAG 虚地址核心复制方式（此前仅 ECMP），PIM ASM/静态 RP 以 M-LAG 虚地址为 RP；新增 CLI `vxlan multicast-group member enable`（VLAN 虚接口视图，commit/XML2CLI/Candidate）、命令下内核和驱动（pfDRV_MC_HandleVxlanMGrpMemChange）、VLAN 接口激活/删除与 up/down 事件、逃生 VLAN 分布式同步与 HA（CFS 双机配置同步）、配置变化联动表项、逃生 VLAN 变化遍历重刷下一跳表项、下一跳表项添加逃生 VLAN 出口与 IPL 出端口、与 PIM SM 使能联动；ISSU 软重启恢复该配置。
- **难点**：peer-link 三层逃生方案（专用 VLAN 虚接口承载 VXLAN 封装逃生报文 + L3_MROUTE_VXLANGRP_MEMBER Flag 下驱动）；peer-link 与隧道/DR 侧隔离原则、奇偶分担导致的不通/多包分析；故障场景（公网/私网 DR 故障、peer-link 故障 MAD 单机）。
- **代码量**：9 个功能点合计 1900 行（C，全部新增），难度系数 1.22，配置插件 10%、用户态 50%。

### 10. EVPN M-LAG 拷机组播 mdd/drni 进程互等优化｜ B70D064SP38XX 分支 ｜ 2.3K 行
- **问题**：EVPN M-LAG 组网带流量拷机时 mdd 打印 LIPC 超时、与 drni 进程互等。根因：data-group MVXLAN 的 MTunnel 口随流量震荡反复创建/删除，mdd 主线程同步等待 IFM 处理，同时 ACL/DRNI/L2VPN 等需回复的外部事件也在主线程同步响应，形成 md→Ifm→acl→md、md→Ifm→drni→md、md→Ifm→segrt→bgp→md 互锁环。
- **方案与实现**：MTunnel 创建/删除改异步（IF_CreateIfAsy/IF_DeleteIfAsy，fd 加入主线程 epoll），新增主线程通知 IFM 线程的消息框架，接口/地址/L3VPN 事件响应移回主线程；待创建/待删除 MTunnel 链实现隧道口复用，创建节点状态机（del/create/DelAndCreate/createAndDel），批量创建一次最多 64 个、删除串行，失败打标记起定时器重刷；data-group 表项状态机（NoInfo/I-P-Tunnel/WaitSPTnl/Delay/S-P-Tunnel）引入 WaitSPTnl 定时器检查 MTunnel 有效性，超规格表项保持 default-group 挂切换失败链；主备倒换后从配置 DBM/运行 DBM 恢复 MTunnel 并与接口管理双向对账；新增两棵 AVL 树维护 MTunnel 状态、Probe 显示命令、HA/route event-log。
- **代码量**：功能点明细合计 2.3K 行（C，用户态，无移植），难度系数约 1.19，2 人。

### 11. 天翼云客户专线交换机 VXLAN 静态组播转发（NETCONF 下发）｜ S6800/S6900F/5940 ｜ 1300 行
- **背景**：金融/证券组播业务上云：组播源在云外经 PIM 与专线交换机（VTEP）打通，接收者在云内宿主机发 IGMPv2/v3 report，由云内 MCGW 截获经控制器通知专线控制器；专线交换机与 VGW 集群公共 VTEP IP 建立静态 VXLAN 隧道，组播封装对应 VNI 入云，多租户按 VNI 隔离。需支持第三方控制器经 NETCONF 动态下发静态 IGMP 组。
- **功能**：MVPN/instance 表 PmsiTunnelType 枚举新增 Ingress-replication 类型（仅 NetworkType 为 EVPN 时允许，同一 VPN 仅一种模式、冲突校验，不支持 IPv6/public-instance）；新增 IGMP/StaticGroups NETCONF 表（IfName/GroupAddr/SourceAddr 三索引），支持 get/set/create/merge/replace/remove/delete/get-bulk，后台复用 `igmp static-group` 命令行流程，组地址合法性检查、源地址全 0 不 buildrun、VSI 口下发定制等规格；交付 XML API 文档、YANG 文件、需求说明书与测试用例。
- **代码量**：约 1300 行（Mvpn/instance 100 + IGMP/staticgroup XML 插件 700 + 后台 500，C），难度系数 0.6，配置插件 30%，用户态 100%。

### 12. 19K-X 适配 Comware V9——EVPN P2MP 组播｜ CR19K-X/SR88 ｜ 3000 行（新开发1000 / 移植2000，折算1610）
- **背景**：EVPN VPLS 缺省头端复制（Ingress Replication），PE-RR 流量随叶子节点膨胀；引入 mLDP P2MP 隧道核心复制（相容隧道 IMET 3 类 + PMSI 属性，选择性隧道 SMET 6 类触发、S-PMSI 10 类通告、(S,G) 按需切换），对标 H 友商。
- **功能**：mcs↔bgpvc 10 类通知消息（ADD_PORT/DEL_PORT/DEL_ENTRY/PROXY_ENABLE、FORWARDMODE、SMOOTH 等），SMET 6 类路由添加/撤销及 8 类路由（ES 对端 leave 同步）；MFIB 新增 P2MP 依赖表项两级树（hP2MPEntryHandle：IP/MAC 表项二级树），下驱动前批量挂接并更新产品信息；P2MP 隧道-L2VIF 变化数据结构（hP2MPChgAvl/hP2MPPortAvl，key 为 VSI/LinkID），隧道变化经 L2VIF 事件回调按 vsi+linkid 遍历依赖表项重刷驱动（新命令字 IPMC_L2_UPDATE_IP_PORT/MAC_PORT）；刷新失败记待处理链定时重刷、主机端口增删加锁原子保护；V9 差异适配（V7 CIOCTL 直下驱动 → V9 经 LIPC 与转发进程 MCS 线程通信、LRPC 远程下驱动）；MFIB 线程与 L2MFIB 线程并发下驱动的 stP2MPEntryMutex 信号量保护；display 命令增加 P2MP 接口类型、multicast record 新增 reflush-l2-ip-port/mac-port 过滤。
- **代码量**：总 3000 行（新开发 1000 / 移植 2000，折算 1610），难度系数 1.446，开发负责人林方钰。

## 三、组播协议特性开发（PIM / IGMP / MSDP / 安全）

### 13. 深交所 PIM Source-Proxy（`pim source-proxy enable`）｜ SR88/B75 ｜ 2200 行（新开发200 / 移植2000）
- **背景**：深交所组播源经腾讯云跨三层接入（腾讯云不支持组播），路由器收到的源与接口不同网段、不认为自己是直连源 DR、不发 PIM 注册，流量不通。对标华为 NE40E/NE800E 组播源代理。
- **功能**：新增接口级命令 `pim source-proxy enable [ policy { ipv4-acl-number | acl-name } ]` 及 IPv6 同款（ACL 2000~3999/3000~3999 按 (S,G) 过滤，ACL 删除检查经 ACL_EV_GROUP_DELETE_CHECK 前后台联动 + PM_ACL_Register 引用计数）；SM 模式接口视为直连源（表项复用 SPT+LOC 标记并新增 SPROXY 标记，满足 LOC+DR+SPT/ACT+RP 可达+非本机 RP 发注册）；DM/SSM 打 LOC 标记、停止向上游发 JP，DM 触发状态刷新；无路由场景以流量入口作表项入接口（PRT_UTL_NewUpStream 返回源代理接口 PRT_UPSTREAM_S，RtInfo 置缺省值，PRT_UTL_IsLocalSource 扩展判断）；WrongIf 切换（旧入口 RtInfo 缺省且新入口配置源代理时切入接口）；display pim routing-table Flag 新增 SPROXY；undo 后不满足 SPT 条件按评审删除重建 (S,G) 表项自动恢复（含 NSR 备份标记）；路由恢复/丢失 15 秒周期检测、SSM no-cache 适配、NETCONF PIM/Ipv4&Ipv6Interfaces 表新增 SourceProxy/SourceProxyPolicy 列。
- **代码量**：总 2200 行（新开发 200 / 移植 2000），14 个功能点，难度系数 1.08，1 人。

### 14. 中金所公平组播（`multicast forwarding fair enable`）｜ SR88/B75 ｜ 1100 行（新开发）+ 微码配合
- **背景**：金融行情组播复制按叶子加入顺序转发，排前出接口先收到流、时延不公平；对标华为 NE40E multicast fair-forward，涉及平台/驱动/微码三层协同。
- **功能**：系统视图新增 `multicast/ipv6 multicast forwarding fair enable`（IPv4/IPv6 命令行分开注册，MRIB 注册并 DBM 备份）；配置链路 MRIB→主控 MFIB（保存驱动返回产品信息）→同步各接口板 MFIB→各板下驱动；驱动新增 pfDRV_MC_FairForward/pfDRV_IPV6MC_FairForward 接口（uiCmdType 正反向、auiDrvContext 跨板上下文），微码出接口间逐包轮询（IF1-IF2-IF3 轮转）；利用微码 MID 计数器（128k）覆盖 IPv4 32k/IPv6 8k/二层约 20k 表项规格，超规格动态分配降级；不支持软转，BIER/NG-MVPN 公网表项不打标记，BRAS 组播支持，MDC 按 MDC 配置；不支持的板驱动返回并输出 syslog（MFIB_FAIR_FWD_NOTSUPPORT，告警成对方案一）、失败定时器重刷；`display system internal multicast record` 新增 set-fair-fwd 过滤；NETCONF Mroute 表新增 FairForwarding 列；simware 定制。
- **代码量**：总 1100 行（新开发，9 个功能点），综合难度系数 1.02，另 SR88 微码组几百行配合。

### 15. MSDP 认证支持 TCP-AO（2025 南网测试）｜ V9 园区核心 ｜ 1000 行（新开发）
- **背景**：2025 南方电网"内生安全"测试，MD5 认证密钥静态绑定需手动更换，无法满足测试例；对标华为实现 RFC5925/5926 TCP-AO 并异构互通。
- **功能**：新增 `peer peer-address tcp-ao tcp-ao-name [ accept-non-ao ]`（与 password/keychain/tcp-ao 互斥，CLI_CFGTREE_FindRec 前台冲突检查）；TCP-AO 多 Key（MKT）管理——每 Key 独立算法（HMAC-SHA-256、AES-128-CMAC 等 9 种）与绝对/周期活跃时间，按 KeyID/RNextKeyID 自动换钥，容忍时间内不断连平滑切换；32 位 SNE 序列号扩展防重放；setsockopt(SOL_TCP, TCP_AO) 实现，accept-non-ao 采用协议模块下发 TCP 选项方案（BGP 不生效、MSDP/LDP 生效）；NSR 备升主重设 TCP_AO 选项、HA M3 批备、MLAG/vSys 天然支持、ISSU 兼容；NETCONF MSDP/Peers 表新增 TcpAoName/TcpAoAcceptNonAo 列；`display msdp peer-status` 扩充认证类型。
- **代码量**：总 1000 行（新开发），难度系数 0.91，1 人。

### 16. 配置安全-组播（MSDP Keychain 认证，人保测试）｜ S10500V7 ｜ 2100 行（新开发）
- **功能**：新增 `peer peer-address keychain keychain-name`（与 password 互斥，setsockopt(SOL_TCP, TCP_KEYCHAIN)）；支持 TCP 可用 5 种算法（MD5/HMAC-MD5/HMAC-SHA-256/SM3/HMAC-SM3，SM3 经 CRYPTO_GetAlgorithmInfo/FIPS 判断）；接入配置安全框架双模式——弱安全模式输出风险提示并 SRISK_AddData/DelData 记录风险项（DBM 全局库、主备备份、首条触发日志与 TRAP），强安全模式下 password 不可配；风险计数 0→1 临界增删、汇总风险；注册 KEYCHAIN_RegEventCB 处理 INSECURE 事件；处理板插拔、备升主（NSR 区分风险计数恢复）、配置恢复一致性；`display msdp peer-status` 增加认证类型，`display system internal msdp statistics` 增加风险计数。
- **代码量**：总 2100 行（新开发，11 个功能点），难度系数 1.0129，2 人。

### 17. Videlco IGMP Plus 补充场景（igmp-snooping NETCONF）｜ B70D064SP38XX ｜ 2500 行（新开发200 / 移植2300）
- **背景**：客户 Videlco 对标 NETGEAR IGMP Plus（WEB 一键下发 NETCONF）；现场测试补充需求：用户不点播时不向路由器端口转发，需支持 `igmp-snooping router-port-discard` 的 NETCONF。
- **功能**：IGMPSnooping/MLDSnooping Configuration 表新增 FastLeave/FastLeaveVlanList 列（方案一，FastLeave 必带）；FastLeaveVlanList 支持 base:incremental 增量 create/merge/replace/delete/remove；VLANs 表新增 RouterPortDiscard 列；新增全局 fast-leave 表；entry-limit/global-enable/host-aging-time/host-tracking/last-member-query-interval/max-response-time/router-aging-time 共 7 条全局命令 NETCONF 补齐；XML2CLI（"1,2,3,5-8,10-20" 与 "1 to 3" 互转，Enabled 列回调方案）；前台 xmlcfgd 与后台 mcsd 交互改造，get 消息不含 vlan bitmap 保 ISSU 兼容，fast-leave bitmap 经独立 TLV（MCS_CFG_BITMAP_VALUE_S）；YANG 仅改文件，gRPC/RESTful 无需特殊修改。
- **代码量**：总 2500 行（新开发 200 / 移植 2300），难度系数 0.8375，配置插件 20%，用户态 100%。开发责任人林方钰。

### 18. Videlco IGMP 协议及 WEB 界面开发（igmp-snooping fast-leave NETCONF）｜ B70D064sp ｜ 2100 行（新开发）
- **功能**：全局视图 `fast-leave [ vlan vlan-list ]` NETCONF（IGMP/MLD 双栈同步），Configuration 表新增 FastLeave/FastLeaveVlanList 列；WEB 一键 IGMP+（触发 fast-leave vlan 101、VLAN 使能、drop-unknown、querier、query-interval 等 NETCONF）；entry-limit/global-enable/host-aging-time/host-tracking/last-member-query-interval/max-response-time/router-aging-time 各 200 行补齐；vlan list 增量下发；XML2CLI 回调方案。
- **难点**：全局表 Enabled 列既普通又对应视图的 xml2cli 三方案对比（选回调函数方案）；vlan list merge 语义（合并 vs 替换）看齐本模块；MCS_XML_CFG_INFO_S 消息不含 vlan bitmap 保证 ISSU 兼容。
- **代码量**：总 2100 行（新开发，前台 400/后台 100/xml2cli 200 + 7 命令各 200），难度系数 0.84，用户态 100%。

### 19. 丢弃 FF10 前缀（scope 0）IPv6 组播报文｜ 12500X-AF/HPE 12900E（K 系列单板）｜ 1500 行（新开发）
- **功能**：新增系统视图 `ipv6 multicast deny scope scope-id`（仅 0）禁学/禁转/禁生成 FF*0 前缀报文，"一禁即禁"；MRIB 集中管控（MRIB_GLB_CFG_S 新增 uiDenyScope，新增 MRIB_MBR_EVENT_SCOPE_GRP_DENY 事件经 MRIB_NOTIFY_MSG_SCOPE_GRP_DENY 通知 PIM6/MLD，新增 MFIB_RT_SET_SCOPE_GRP_DENY 枚举置于末尾保 ISSU）；MLD（GMP_CanPassGroupPolicy）、PIM6（PIMMAIN_FilterSource）、MFIB（MFIB_VRF_IsSourceFilterPermit）三处过滤检查；与 source-policy/group-policy 冲突时任一禁止即禁止；PIM 侧 VRF 15 秒周期遍历打删除标记并通知下游重报加入（SM/DM/SSM/双向）；MLD 主线程转 EVENT 线程分批遍历删/恢静态与动态组；undo 后恢复 FF*0 静态组；平滑新增消息类型，HA M3 模型经 mribGmpHaL3mc NSR 备份。
- **代码量**：总 1500 行（命令行 500/MRIB 150/MFIB 50/MLD 350/PIM 250/平滑 150/HA 50），难度中，2 人。

### 20. 组播一体化BRAS（可控组播）V9 支持 ｜ CR19K-X / Comware V9 ｜ 11200 行（新开发3200 / 移植8000，折算4630）
- **背景**：BRAS 组播即"可控组播"——宽带接入服务器上按用户（PPPoE/IPoE）对组播点播做认证、复制与隔离：普通组播出接口目的 MAC 为组播 MAC、用户间不隔离，可控组播为每个上线用户分配虚拟 MUA 口（目的 MAC 为用户单播 MAC），实现每用户隔离复制。SR88/B75 分支已有主体实现，V9（CR19K-X）此前仅合入代码未打开定制；动态 VLAN 复制对标华为 NE40E 的 copy by-vlan 复制模式（华为按端口+VLAN、by-session、user-aggregation、by-port 四种复制模式），显示统计能力对标华为 `display multicast group-ip`。
- **功能**（6 个子需求）：① BRAS 组播基础——移植 `igmp authorization-enable`、`igmp access-policy`、`igmp join-by-session [mode {both|bras|non-bras}]`、`igmp user-vlan-aggregation`、`igmp static-group ... dot1q vid`、`igmp attack-defense` 等可控组播命令；MUA 口/base 口-派生口（cfgIf/runIf）模型与 base 口状态机；IGMP/PIM NSR（备份动态组、proxy 接口/组、base/派生口、PIM 路由表、ifState 状态机、邻居/BSR/RP 等）；接入模块经 `MCAST_USER_Register/MCAST_USER_Dispatch` 通知用户上下线；静态组 HA 消息结构重构（`GMP_HA_STATIC_VLAN_GROUP_S` 拆出变长位图为 `GMP_HA_VLAN_BITMAP_S`）保 ISSU 兼容。② UCM 统一用户管理适配——用户信息改由 UCM 统一管理（User-ID 不再含接入类型，新增 Session-ID/Subscriber-ID 维护于 `MUSER_AUTH_INFO_S`），PPPoE 组播配置从 VT 口迁移至物理口，支持 `trace access-user` 用户级 Trace。③ 可控组播 NETCONF 移植——IGMP/MLD Interfaces 表新增 AuthEnabled/JoinBySession/UserAggOuterVlan/UserAggInnerVlan 列，新增 IGMP/MLD UserProfiles 表（UserProfileName/AccessPolicy），XML2CLI 同步支持。④ 动态 VLAN 复制——`igmp user-vlan-aggregation dynamic`，mrib lib 以 UserLabel/MUA ifIndex 为 Key 维护两棵树、MUA 下建二级树，经 UserLabel 查用户信息过授权策略，模式切换要求用户全部下线。⑤ 显示命令增强——`display igmp user-info ... [active-group | active-user | inactive-user] [statistics]`、`display igmp group ... [statistics]`（Dynamic/Static groups in total），新增 `gmpCfgShowUserAuthCheckAndCount`、`GMP_CMD_SHOW_GROUP_S` 等。⑥ 用户信息新字段下驱动——`MUSER_AUTH_INFO_S` 新增 uiUcmIndex/usBrasHash 下发驱动 MLL 用于负载分担，前后域切换/二次认证先删后加，`display igmp user-info` 增加 UCM Index/BRAS hash 字段。
- **难点**：IGMP/PIM NSR 大量运行数据（动态组、MUA 派生口、用户上下线消息、VSRP 虚拟封装等）实备与备升主恢复（cfgIf 链路状态重取、runIf/组定时器重启、临时 AVL 树恢复封装-MUA 对应关系）；含变长位图的 HA 消息结构无法扩展需拆分新结构实现 ISSU 新老兼容；B75→V9 移植与二层可控组播共用 lib、MVXLAN proxy/m-lag 等特性代码冲突逐行同步；V9 全量字节序转换、下驱动改 LRPC 远程调用；1M PPPoE/512K IPoE 双栈会话规格下的内存与性能约束。
- **代码量**：总 11200 行（新开发 3200 / 移植 8000，折算 4630），难度系数 1.147，用户态占比 90%，3 人，依赖 UCM/PPP/PPPoE/IPoE/L2TP。

### 21. MLAG 易用性可维护性优化（组播）｜ V7（S68/S10500v7/S5560X）｜ 1300 行
- **功能**：命令同步规则梳理——按 M-LAG 框架修改同步 conf：PIM anycast-rp/c-bsr/c-rp、MRIB 静态路由、MSDP originating-rp/peer/shutdown 等设为可同步；MVXLAN m-lag local remote 为两端必不同的对称配置；multicast-vpn vxlan edge remote 与 mtrace 不同步。配置缺失检查提示——命令行插件回调向进程发 Check 消息回显，共 10 项检查（MVXLAN 5 项：source 必须带 evpn-mlag-group 且接口地址一致、m-lag local remote 三种方式优先级提示、edge remote 检查；PIM 3 项：VLANIF/VSI 使能 PIM 检查 pim-snooping、IPL 逃生 VLAN 提示；IGMP 2 项），MVXLAN 经 L2VPN 事件感知 evpn m-lag group 地址，PIM/IGMP 关注 VLAN_EVENT_VLAN_DR_PA_CHANGE 维护 DR VLAN 位图并从 MFIB 取 snooping 使能。配置简化——M-LAG 下 VLAN 虚接口免配 pim distributed-dr/passive：在 PimNbr_IsDR 判断处查询 VLAN 内存在 M-LAG DR 口即视为满足 DR 条件（注册 VLAN 事件、DR 位图更新到 IFParam、条件变化重走 PM_NBR_ElectDR）；MVXLAN source/m-lag local remote 直接采纳 evpn m-lag local 配置。
- **难点**：DR 语义重构（协议规定仅 DR 口加组播出口，但 M-LAG 直连接收者时两侧须均作出口），需在注册/添加出口/DF 竞选等四类场景分别处理；支持 ISSU/IRF/进程亲和性。
- **代码量**：MVXLAN 400 + PIM 500 + IGMP 400 = 1300 行（C），难度系数 0.88，用户态 70%。

## 四、高端路由器 BIER / FRR / 19K-X 适配

### 22. MSR6 BE 支持 FRR-MCAST（移动新技术 2023）｜ CR/SR88 B75 ｜ 9.7K LOC
- **功能**：MVPN 双根 1:1 温备保护（draft-wang-bess-mvpn-upstream-df-selection-07）——UMH 路由新增 IDF 协商 BGP 团体属性，支持 MVPN 实例粒度与 (C-S,C-G) HASH 粒度两种 IDF 主动协商选举，新增 warm-root-standby、df-selection source-group 命令（MVPN IPv4/IPv6 + 公网 GTM）；备 IDF 预置未激活备 BIER 隧道出口下 MFIB（不下驱动）并向主 IDF 引流（C-multicast 加入主 IDF PMSI Tunnel），流量检测感知主 IDF/源侧路径故障后备 IDF 快速升主下驱动切换；尾端基于 Root PE 列表"任收"RPF 检查，主备入接口共存下驱动。BIER 隧道本地保护（FRR）——BIERRIB 接收 ISIS 主备邻居/下一跳多级信息，计算主 BIFT 与备份 B-BIFT（F-BM/BF-BM、Plain/Explicit 备份动作、BEA 激活标志）下 BIERFIB 与驱动；支持 LFA（无环校验）与 TI-LFA（扩展 P/Q 空间、Repair List、SRH 显式路径）。故障检测：接口 Down 快切、BFD（primary-path-detect bfd ctrl/echo、primary-neighbor-detect bfd ctrl 多跳）；复用 multicast frr mode/monitor cycle（缺省 200ms）/wtr（缺省 600s）；正切/回切防微环（延时收敛/显式路径）；跨域 BGP bfr-id range 防环路；新增 display bier routing-table 与 NETCONF 模型，支持 Commit/RBAC/ISSU。
- **难点**：用户态/内核态协同（内核态 BIER 本地保护表项下发与切换、BFD 故障快切，板间 LIPC、主备 DBM 同步）；跨域 BFR-prefix 代理成环（部署约束）；双主问题经流量检测 + 本地 FRR 规避；尾端 SA 时序将表项刷新调整至 MFIB 更新 SA 阶段。难度/影响度/风险均评级"高"。
- **代码量**：总 9.7K LOC（约 30 个功能点，C，无移植，用户态 40%、配置插件 8%），难度系数 1.43，4 人。

### 23. 电信 STN 集采 BIERv6 移植-组播｜ SR88/CR B75 ｜ 5.1K LOC（全部移植）
- **功能**：NG-MVPN 支持 BIERv6 隧道（IPv6 网络下 BIER IPv6 封装，基于既有 G-BIER 适配）：新增 `src-dt4/src-dt6 locator sid` 命令经 SRv6 locator+SID 生成 MVPN IPv4/IPv6 隧道源地址，两级 AVL 树（locator name → ipv6-sid）维护 AF 信息与下发状态，跨 AF 冲突检查；调用 SRV6_SID_Occupy/Free 占用释放 SID（新增 SRV6_FUNC_SRCDT4/SRCDT6），响应 SRMS_NOTIFY_* / STATICSID_AVAILABLE 事件重占位；组播与 SRv6 备升主平滑全流程；MVPN 1/3 类路由改用 SRv6 Service Sub TLVs 携带源地址（新增 BGP_MVPN_SUBMSG_BIERV6_SRC_SID_ATTR），G-BIER/BIERv6 双 TLV 按 sub-domain 封装模式选源；BIERFIB 通知增加封装模式字段，MVPN 以 SD 为 key 保存模式，模式变化复用 ipv6 underlay enable 变更处理；新增 `display multicast-bierv6-source configuration`，BIER 配置显示增加 Mode 字段；支撑 ISSU/IRF/进程亲和性，保持跨域。
- **代码量**：总 5.1K LOC（移植，11 个功能点各 150~500），整体难度"较高"，2 人。

### 24. 19K-X 适配 Comware V9——BIER 驱动接口适配｜ CR19K-X/SR88 ｜ 5800 行（新开发）
- **背景**：V7 BIER 下驱动为平台与驱动同进程函数调用（BIER_DRV_Register 注册 HandleBIFTChange/FrrChange/EntryChange/TunnelChange 四类接口），V9 转发/驱动进程分离，需重新设计。
- **功能**：转发进程侧统一驱动接口 DRV_BIER_HandleChange(uiLen, pBuf)，四类接口重新设计为多级 TLV（顶层打包类型 BIER_DRV_TOP_PACK，同一 PACK 子 TLV 继承前序 DrvContext 结果）；适配层三态分发——dlopen libdrv_bier.so 取产品实现、产品支持 LRPC 时经 LRPC_ClientCall 长连接 + 共享内存（SHM_INOUT）调驱动进程侧 BIER_HandleChangeInDrv、否则平台桩函数（simware）；LRPC 方案评审采用"产品实现 V7 驱动接口"，平台提供 liblrpcplug_bier.so 解析 TLV 还原 V7 形式（VNHandle 改 VNID）；下驱动失败重刷经 LIPC 消息（复用 LIPC_LOCAL_PORT_BIERFIB）；配套 simware 驱动桩（libdrv_bier_simware.so + CLI 插件，debugging/set 返回值/display state）；MVPN SA 信息驱动接口（新命令字 IPMC_SET_MCAST_SERVICE_ID）、NPS 单板私网 MLL 表 BIER 出接口、NG-MVPN P2MP 隧道 VN 适配（同时下发 VN ID + VN 信息，新增 IPMC_INFO_OIFVN/OIFNHLFE 子 TLV）。
- **难点**：V7 一对一函数调用改 TLV 打包后子 TLV 依赖前序 DrvContext；组播表项频繁大批量下驱动用 LIPC 长连接 + 共享内存保证性能；消息结构 ISSU 结构。
- **代码量**：总 5800 行（新开发，26 个功能点），难度系数 1.5557，3 人。

### 25. 19K-X 适配 Comware V9——组播补齐（B70 MULTICAST EVPN 一期移植）｜ CR19K-X/SR88 ｜ 75.8K LOC（移植65.2K / 新增10.6K）
- **内容**：将 V7 B70 分支组播 VXLAN 基础特性整体移植到 19K-X 平台 V9（7 个来源需求：广电核心复制、腾讯手工 VXLAN 三层组播、北京 11 号线 M-LAG、S5560X DRNI IGMP Proxy、125G EVPN 组播 IPv6、6800 EVPN VXLAN 二层组播 IGMP PROXY、DRNI 改名 M-LAG）。功能点同第 6 项（MVXLAN/IGMP Proxy/M-LAG/EVPN IPv6/V9 通信适配/COMMIT），区别在于目标平台为 19K-X/SR88 路由器、B 类项目，重点在 V7→V9 线程模型与消息框架差异适配（MFIB 移入转发进程独立线程、MFIB_TLV_HEAD_S 多子 TLV、驱动接口收敛 DRV_MC_HandleMrouteChange、LIPC 对齐与字节序转换）。
- **代码量**：一期 75.8K LOC（与二期合并 88.2K），难度系数 1.2539，整体难度高。

## 五、V9 trunk 特性补齐与可维护性

### 26. 园区交换机 B70 特性同步到 V9 trunk——MCAST 二期｜ V9 trunk ｜ 25350 行（移植18350 / 新开发7000）
- **功能**（7 项特性，57 个功能点）：跨 VPN 组播（MRIB/IPv6 MRIB 视图 `multicast extranet select-rpf`，SM/SSM/BIDIR-SM 三模式下入 VPN downstream/出 VPN upstream 状态机特殊处理，VPN 引入引出虚拟接口扩展兼容 NBMA/MUA/MUPE，内核 MFIB 跨 VPN 表项与板间同步，PIM display extranet 显示，IPv4/IPv6 NETCONF）；组播可维护性（MRIB MBR event-log 移植，display/reset/size 命令，约 200 种二级类型 log lib 化，约 15 类流程埋点）；MVPN event-log（route/HA/BGP 1/3/4/5/7 类路由、MDT、MBR、RSVP-TE、mLDP 日志）；PIM/MRIB/IGMP/MSDP/组播 VXLAN 支持地址借用；c-bsr holdtime/interval 快速切换 RP；`multicast permit ssdp-group` 默认过滤 SSDP 组贯穿 MRIB/IGMP/PIM/MFIB；`multicast cpu-forwarding max-copy-count` 软转复制上限（含 NSR/平滑/netconf）；MVPN MDT 支持私网 IPv6。
- **代码量**：总 25350 行（移植 18350 / 新开发 7000），难度系数约 1.34，3 人。

### 27. B70 MULTICAST trap 补齐｜ V9 trunk ｜ 7800 行（移植6800 / 新开发1000）
- **功能**：补齐 V9 组播 SNMP trap：新增 `snmp-agent trap enable igmp [join|leave]`、`igmp-snooping [entry-refresh-failed]`、`mld [join|leave]`、`mld-snooping [entry-refresh-failed]`；PIM/PIM6 新增 elected-bsr-lost-election、interface-election、invalid-join-prune、invalid-register、private-interface-election、private-neighbor-loss、private-new-neighbor、private-rp-mapping-change、rp-mapping-change 等开关节点；补齐私有 PIM（hh3cPimNeighborAdd/Loss、hh3cPimRPMappingChange、hh3cPimInterfaceElection）、公有 PIM（pimInvalidRegister/pimInvalidJoinPrune/pimRPMappingChange/pimInterfaceElection）、私有 MCS（hh3cMcsEntryRefreshFailAlarm）、私有 IGMP/MLD（hh3cMgmdStdGmpJoin/Leave）告警节点及全局 pimRPMappingNotificationPeriod；复用 PIM trap 框架抽取公共框架（约 300 行/模块）向 IGMP/MLD/MCS 推广（PM_TRAP_Init/Fini、PimTrap_ProcEpollEvent、MIB tree/notify、CLI 注册 PIM_CLI_ParsePimTrap/PimCfg_CfgTrap），trap 输出走 SNMP 接口并预留限速（PimTrap_RateLimit）。
- **代码量**：总 7800 行（移植 6800 / 新开发 1000），难度系数约 0.78。

### 28. YANG 约束检查-组播（EANTC 测试复盘）｜ V9 trunk S12500 ｜ 2700 行（新开发）
- **背景**：思科 NSO 控制器下发配置时前台不报错、到设备才失败；目标是"能用 YANG 检查的都得用 YANG 检查，不能用的说明原因"。
- **功能**：对 IGMP/MLD/Mroute/PIM/MVPN/MSDP/IGMPSnooping/MLDSnooping/PIMSnooping 九个模块 YANG 模型补齐约束：default/units/description；leafref 引用（VRF→l3vpn、IfIndex/IfName→ifmgr、VLAN→vlan、VsiName→L2VPN、MSDP Peers VRF→MSDP Instances）；pattern 正则实现 IPv4/IPv6 单播与组播地址合法性（十余种，含排除回环/linklocal/组播/保留段、管理域 239 段）；acl number/name 联合体范围检查（2000-2999/3000-3999/2000-3999 分场景）；must 列间关系（KeepaliveInterval<Holdtime、Extranet SpecifySource/SpecifyGroup 不能同为 false、源/接收 VPN 不同、L3VNI 与私网冲突等）；when 配置依赖（snooping 依赖全局使能）；choice case 互斥（PIM JoinPolicy）；max-elements 实例规格；count() 实现 VxlanMGrpMem 仅一接口使能；产品 deviation（NsrEnable、CpuMaxCopyCount、MVPN 枚举裁剪等）。
- **难点**：逐表梳理 NSO 实测失败场景归因；YANG 检查基于数据无法区分 create/delete、无法引用 data 表、无法处理联动删除等场景逐一确认"无法用 YANG"并说明；NSO 空串输入限制推动 L3VPN 用 "__public__" 表示公网。
- **代码量**：总 2700 行（IGMP/MLD 各 300、Mroute/PIM 各 400、MVPN/Snooping 各 300、MSDP/PIMSnooping 各 100、公共 200），2 人。

### 29. 全特性单机 ISSU——二层组播（igmp/mld/pim snooping）｜ 园区接入 S9820/S6550x ｜ 1800 行（新开发）
- **功能**：V9 单机 ISSU 软重启不中断流量：旧主容器 FWD_MFIB/MCS 响应 DEV_EVT_PRESOFTREBOOT_HIGH 记录全局变量、FWMCS 不再处理 MCS 消息不下驱动；备 MCS 新增"从主 FWD_MFIB 拉 MSIB 表项"流程，创建带 kernel 标记的 MSIB 表项、下发 FWD_MCS/FWD_MFIB 建转发表但不下驱动；升级前后表项区分——平滑消息恢复"升级前已建表项"（建 group 表项、清 kernel 标记、不下发 FWD_MCS），升级期间新建表项下驱动并通知 FWD_MFIB，升级期间删除表项的 kernel 标记残留于平滑后检查删除；FWD_MCS 下驱动区分采用新增专用消息类型（拉数据前禁止下驱动、拉完恢复）；ISSU cancel（DEV_EVT_SOFTREBOOT_CANCEL_HIGH）重置全局变量走进程重启流程；IPv4/IPv6 双栈，HA 模型 M2，涉及 MCS/MFIB/FWD_MFIB/FWD_MCS/MSIB 模块。
- **代码量**：总 1800 行（新开发，12 个功能点，MCS 侧 1050 / MFIB 侧 750），难度系数 1.61，3 人。

### 30. 全特性单机 ISSU——三层组播｜ 园区接入 S9820-8M ｜ 1800 行（新开发）
- **功能**：所有三层组播特性、组播 VLAN、二层组播 VXLAN 支持单机 ISSU 软重启：旧主 MFIB 响应 presoftreboot 置全局变量、不处理 PIM 消息不板间同步；备 MFIB 走原板插入流程从旧主 FWD_MFIB 拉数据（含出接口/出端口/drvcontext），拉完才回复 Fnotify_IamReady（新增 Fnotify_Register 防过早 ready）；dummy 表项、大规格下驱动失败/绑定复制资源失败表项同步备板（软件信息不下驱动）防驱动残留；IGMP/MLD/PIM/IPv6 PIM 实现默认 NSR（新增 `igmp/mld/pim/ipv6 pim non-stop-routing`，缺省值与型号相关），PIM 备从主拉数据不下发 MFIB、批备结束消息 PIMHA_NSR_BATCH_END 后才置 running；升级期间表项增删由 PIM 主通知 PIM 备，MFIB 忽略 PIM 消息，备升主后平滑时才下驱动（ISSU 时长约 4 分钟）；二三层混跑 presoftreboot 后二层表项变化不扩展三层；组播 VLAN 与三层组播共用全局变量；未使能 NSR 时 ISSU 期间表项仅等老化。
- **难点**："能通过现有数据恢复的不走 ISSU 文件"（省内存），MFIB 表项与 drvcontext 全程与驱动一致、不重复下驱动；平台先于驱动响应 presoftreboot 的时序保证。
- **代码量**：总 1800 行（新开发，14 个功能点），难度系数 1.61，2 人。

---

## 附注
- `项目SOW/` 下共 31 份任务书，本文档 30 个条目一一对应（B70 MULTICAST EVPN 二期的 V7V9 特性补齐任务书为同一条目第 7 项，不再单列）。
- 所有命令、函数名、消息名、LOC 数字均引自任务书原文；"折算"行为任务书官方折算值。
