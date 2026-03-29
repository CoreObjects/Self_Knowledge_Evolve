
# 网络通信领域本体设计文档

**版本**：v0.2
**状态**：五层语义结构重构版
**更新说明**：基于《面向网络通信工程知识组织的认知科学与知识工程框架综述》及《数通域最小实验单元本体重构》，将原 v0.1 概念树式设计全面升级为"概念—机制—方法—条件—场景"五层语义本体结构。

---

# 1. 文档目标

本文档定义网络通信领域的本体模型，作为语义知识库的目录、索引和关系组织结构。

**v0.2 核心升级**：本体不再只是"术语目录"，而是一套可支撑以下工程任务全闭环的多层知识对象组织框架：

- 概念检索：某技术是什么
- 原理解释：某方案为什么这样工作
- 方法输出：某业务怎么配置和验证
- 条件筛选：何时应采用某技术路线
- 场景检索：某业务背景下有哪些可复用方案模式

本体同时继承 v0.1 的以下核心能力：
- 分类归档
- 标签映射
- 术语归一（跨厂商归一化）
- 关系建模
- 依赖分析
- 影响传播
- 受控演化

---

# 2. 本体设计原则

## 2.1 骨架优先

本体首先承担"骨架"职责，不承载所有细枝末节知识。
优先定义：稳定概念、清晰层次、受控关系、统一命名、基本约束。

## 2.2 从"概念树"升级为"五层语义结构"

旧式本体以协议/设备/特性为主轴建树，便于收纳定义，但无法表达：

- 为什么某机制在某场景有效
- 如何组合多个协议能力完成业务
- 哪些配置对象存在依赖与顺序
- 何时采用某方案、何时禁止使用

因此，新本体不再以协议树为唯一主轴，而改为以五层语义结构组织：

| 层 | 核心问题 | 知识类型 | 理论对应 |
|----|---------|---------|---------|
| 概念层（Concept） | 是什么 | 陈述性知识 | CommonKADS 领域知识、Frame 对象槽位 |
| 机制层（Mechanism） | 为什么 | 深层原理知识 | Inference support、Frame 因果槽位 |
| 方法层（Method） | 怎么做 | 程序性知识 | Script 理论、CommonKADS 任务执行 |
| 条件层（Condition） | 何时用 | 条件性知识 | 规则系统、CommonKADS 推理控制 |
| 场景层（Scenario） | 在什么业务背景下组合应用 | 情景知识 | Frame 情景、Case-based reasoning |

## 2.3 本体对象不止概念节点

需要显式建模至少七类知识对象：

- **ConceptNode**：对象与能力实体
- **MechanismNode**：动态原理与因果机制
- **MethodNode**：配置、验证、排障、实施方法
- **ConditionRuleNode**：适用条件、约束、禁忌、决策规则
- **ScenarioPatternNode**：典型业务场景与方案模式
- **CaseNode**：工程案例（场景模式的具体实例化）
- **EvidenceNode**：知识来源与证据支撑

## 2.4 语义稳定与术语变化分离

- **Canonical Concept**：稳定概念（核心层）
- **Alias / Lexicon**：别名、缩写、厂商术语（词汇层）
- **Candidate Concept**：候选新概念（候选层）

## 2.5 关系受控

本体中的边必须属于受控关系类型集合。层内关系与跨层关系分别管理。

## 2.6 以工程闭环作为知识完整性边界

知识版图是否完整，不能仅看协议和概念覆盖度，而要看是否能支撑：

> 业务需求 → 能力映射 → 技术选型 → 逻辑设计 → 配置落地 → 验证验收 → 运维处理

## 2.7 演化可回滚

本体版本化管理，支持差异比较、影响分析和回滚。

---

# 3. 本体总体架构

本体采用两个维度的组织方式：

**纵向（通用层次）**：
1. 顶层抽象本体
2. 通信领域一级域本体
3. 子域本体
4. 词汇与别名层

**横向（知识类型）**：
1. 概念层（Concept Layer）
2. 机制层（Mechanism Layer）
3. 方法层（Method Layer）
4. 条件层（Condition Layer）
5. 场景层（Scenario Layer）

两个维度在子域层交汇：每个子域（如 IP/数通域）都应在五个知识类型层上均有覆盖。

---

# 4. 顶层抽象本体

顶层本体定义网络通信世界中最稳定的一组抽象类别。

## 4.1 实体类（Entity）

表示可被识别的对象、资源或结构单元。

### 顶层实体类
- Network
- Domain
- Site
- Node
- Device
- Module
- Board
- Port
- Interface
- Link
- Topology
- Path
- Tunnel
- Service
- User
- Subscriber
- Tenant
- Resource
- Policy
- ProtocolInstance
- ConfigurationItem
- Alarm
- Fault
- Event
- KPI
- Metric
- TrafficFlow
- SecurityObject
- Document
- EvidenceSource

## 4.2 行为类（Behavior / Process）

表示网络中的功能行为、机制或过程。

- Forwarding
- Routing
- Signaling
- Encapsulation
- Authentication
- Authorization
- Scheduling
- TrafficEngineering
- ProtectionSwitching
- OAM
- ServiceProvisioning
- FaultDiagnosis
- ResourceAllocation
- SessionEstablishment
- TelemetryCollection
- PolicyEnforcement

## 4.3 规则类（Rule / Constraint）

表示约束、依赖和规则。

- DependencyRule
- CompatibilityRule
- ReachabilityRule
- ConfigurationConstraint
- ProtocolConstraint
- SecurityConstraint
- SLAConstraint
- CapacityConstraint
- TimingConstraint

## 4.4 状态类（State）

表示对象或过程的运行状态。

- Up
- Down
- Degraded
- Active
- Standby
- Converged
- Flapping
- Congested
- Authenticated
- Unauthorized
- Healthy
- Faulty
- Synchronized
- Unsynchronized

## 4.5 证据类（Evidence）

表示对知识主张提供支撑的来源与证据。

- StandardClause
- VendorDocSection
- WebArticleChunk
- ConfigSnippet
- LogSnippet
- AlarmRecord
- TelemetrySample
- TroubleshootingCase

---

# 5. 通信领域一级域本体

建议定义以下一级域：

1. Physical Infrastructure
2. Access Network
3. IP / Data Communication Network
4. Optical Network
5. Transport Network
6. Mobile Access & Core Network
7. Data Center / Cloud Network
8. Network Management & OAM
9. Security
10. Service & Business
11. Operations & Fault
12. Configuration & Automation

---

# 6. 一级域本体展开

## 6.1 Physical Infrastructure

描述通信网络的物理承载对象。

### 核心概念
- Site / Room / Rack / Chassis / Shelf / Board / Module / Slot
- PowerSupply / Fan / Cable / Fiber / PatchPanel / Connector / Port
- OpticalModule / Antenna / GPSClock

### 核心关系
- contains / mounted_on / connected_by / powered_by / located_at / part_of

---

## 6.2 Access Network

描述接入网络对象及机制。

### 核心概念
- OLT / ONU / ONT / PON / GPON / XG-PON / XGS-PON / 10G-EPON
- T-CONT / GEM-Port / DBA / Access-Service / Access-Profile
- VLAN / QinQ / Authentication-Profile

### 核心关系
- serves / aggregates / allocates / encapsulates / binds_to / depends_on

---

## 6.3 IP / Data Communication Network

本域是五层语义结构的重点展开子域。详见第 8 章"数通域五层本体"。

此处仅列一级概念目录：

### 概念层核心对象（Concept）
- 二层：Ethernet / MAC / VLAN / QinQ / STP / RSTP / MSTP / LACP / LLDP
- 三层：IPv4 / IPv6 / ARP / ND / ICMP / DHCP / DNS / NAT
- 路由：OSPF / IS-IS / BGP / StaticRoute / RoutePolicy / PrefixList / Community / RouteReflector / VRRP
- MPLS/SR：MPLS / LDP / RSVP-TE / SR-MPLS / SRv6 / Label / LSP / Tunnel / TE-Policy
- VPN/Overlay：VRF / L2VPN / L3VPN / VPLS / EVPN / VXLAN / EVPN-VXLAN / VTEP / BridgeDomain
- QoS：Classifier / Behavior / Queue / Scheduler / Policer / Shaper / DropProfile
- 安全/控制：ACL / NATPolicy / IPsec / GRE / BFD

### 机制层核心对象（Mechanism）
见第 8.2 节。

### 方法层核心对象（Method）
见第 8.3 节。

### 条件层核心对象（Condition）
见第 8.4 节。

### 场景层核心对象（Scenario）
见第 8.5 节。

---

## 6.4 Optical Network

描述光传输与光层对象。

### 核心概念
- OTN / WDM / DWDM / CWDM / ROADM
- OCh / OMS / OTS / ODU / ODUk / OTU / OTUk
- Lambda / OpticalPath / OpticalSpan / OpticalPower / OSNR / BER / FEC / OpticalProtection

### 核心关系
- multiplexes / transports / terminates / amplifies / switches / protects / monitored_by

---

## 6.5 Transport Network

描述承载与同步相关知识。

### 核心概念
- PTN / SDH / MPLS-TP / CarrierEthernet
- SyncE / IEEE1588v2 / PTP / Clock / BoundaryClock / TransparentClock / ClockDomain / TimingSource

### 核心关系
- synchronizes_with / distributes_time_to / transports / depends_on / protects

---

## 6.6 Mobile Access & Core Network

描述无线接入和核心网知识。

### 接入侧概念
- UE / gNB / eNB / Cell / DU / CU / RAN-Function

### 核心网概念
- AMF / SMF / UPF / AUSF / UDM / PCF / NRF / NSSF / NEF / AF
- Session / PDU-Session / Bearer / Slice / QoS-Flow

### 协议与接口
- GTP / PFCP / Diameter / HTTP2-SBA / N1 / N2 / N3 / N4 / N6

### 核心关系
- authenticates / selects / anchors / manages_session_for
- exchanges_signaling_with / forwards_user_plane_for / applies_policy_to

---

## 6.7 Data Center / Cloud Network

描述数据中心与云网络知识。

### 核心概念
- Spine / Leaf / TOR / Overlay / Underlay / EVPN-VXLAN / VTEP
- TenantNetwork / SecurityGroup / LoadBalancer / ServiceChain / VirtualRouter

### 核心关系
- peers_with / overlays_on / isolates / load_balances / chained_with

---

## 6.8 Network Management & OAM

描述管理、监控和运维观测体系。

### 核心概念
- NMS / EMS / Controller / Inventory / Telemetry / PM / FM / CM
- Netconf / YANG / SNMP / gNMI / Syslog / Trace / OAMSession / SLAProbe

### 核心关系
- collects / monitors / configures / controls / inventories / reports / alarms_on

---

## 6.9 Security

描述网络安全对象与控制机制。

### 核心概念
- SecurityPolicy / ACL / Firewall / IDS / IPS / VPN / IPsec / MACsec
- AAA / RADIUS / TACACS+ / Certificate / Key / TrustDomain

### 核心关系
- authenticates / authorizes / encrypts / filters / protects / isolates

---

## 6.10 Service & Business

描述业务与租户视角的概念。

### 核心概念
- Service / ServiceInstance / VPNService / InternetAccessService
- LeasedLineService / VoiceService / VideoService / EnterpriseTenant
- SLA / UserPlaneService / BusinessIntent

### 核心关系
- delivered_by / depends_on / measured_by / bound_to / offered_to

---

## 6.11 Operations & Fault

描述故障、症状、根因、影响和恢复。

### 核心概念
- Alarm / Fault / Symptom / RootCause / ImpactScope
- RecoveryAction / MaintenanceWindow / Incident / ChangeTask / FaultDomain

### 核心关系
- raises_alarm / indicates / caused_by / impacts / correlated_with / mitigated_by / verified_by

---

## 6.12 Configuration & Automation

描述配置、意图、参数依赖和自动化对象。

### 核心概念
- Command / Parameter / ConfigObject / ConfigBlock / Dependency
- Precondition / Postcondition / ValidationCheck / Template
- PolicyIntent / Workflow / Playbook / Schema / ASTNode

### 核心关系
- configures / depends_on / requires / declares / validates / expands_to / generated_from / references

---

# 7. 关系类型体系

关系类型必须独立建模，分为**层内关系**和**跨层关系**两类。

## 7.1 层内关系

### 分类关系
- is_a / subclass_of / instance_of / part_of / belongs_to_domain

### 结构关系
- contains / hosted_on / mounted_on / connected_to / terminates_on / peers_with

### 协议与功能关系
- uses_protocol / implements / establishes / advertises / learns
- encapsulates / forwards_via / synchronizes_with / authenticates / authorizes / encrypts / protects

### 依赖关系
- depends_on / requires / precedes / conflicts_with / constrained_by / inherits_policy_from

### 运维关系
- raises_alarm / impacts / causes / correlated_with / mitigated_by / verified_by / monitored_by / configured_by

### 证据关系
- supported_by / described_in / derived_from / mentioned_in / contradicted_by

## 7.2 跨层关系（五层语义结构核心）

这是 v0.2 新增的关键关系类型，用于连通五个知识层：

| 关系谓词 | 方向 | 语义 |
|---------|------|------|
| `participates_in` | Concept → Mechanism | 概念参与某机制 |
| `explains` | Mechanism → Concept | 机制解释概念的行为 |
| `implemented_by` | Mechanism → Method | 机制由某方法实现 |
| `operates_on` | Method → Concept | 方法作用于某概念对象 |
| `produces` | Method → Concept | 方法产出某状态或对象 |
| `governed_by` | Method → ConditionRule | 方法受某条件约束 |
| `applies_to` | ConditionRule → Concept/Method | 条件规则约束某概念或方法 |
| `contraindicates` | ConditionRule → Method/Scenario | 条件规则排斥某方法或场景 |
| `selects` | ConditionRule → Method/Scenario | 条件规则选择某方法或场景 |
| `risky_under` | Method/Scenario → ConditionRule | 在某条件下存在风险 |
| `composed_of` | Scenario → Concept/Mechanism/Method | 场景由多个对象组成 |
| `validated_by` | Scenario/Method → VerificationMethod | 场景或方法由验证方法证明 |
| `instantiated_as` | ScenarioPattern → CaseNode | 场景模式在案例中实例化 |
| `applicable_when` | ConditionRule → Scenario | 条件约束场景的适用范围 |
| `risks` | ConditionRule → Scenario | 条件层给出场景风险 |
| `supported_by` | 任意知识节点 → EvidenceNode | 知识单元由证据支持 |

---

# 8. 数通域五层本体（首版重点子域）

IP/数通域是五层语义结构的首个深挖子域，也是最小实验单元。

## 8.1 概念层（Concept Layer）

回答"是什么"。概念层为后续各层提供稳定锚点。

### A. NetworkObject
- Network / Site / Zone / Segment / VRF / VLAN / VNI / Subnet / RouteTarget / Prefix

### B. DeviceObject
- Router / Switch / PE / P / CE / RR / Firewall / LoadBalancer / Gateway

### C. InterfaceAndLinkObject
- Interface / SubInterface / Loopback / Trunk / AccessPort
- PhysicalLink / LogicalLink / Tunnel / LSP

### D. ProtocolObject
- Ethernet / ARP / IPv4 / IPv6 / ICMP / TCP / UDP
- OSPF / IS-IS / BGP / MPLS / LDP / RSVP-TE
- EVPN / VXLAN / VRRP / BFD / DHCP / NAT

### E. PolicyObject
- ACL / RoutePolicy / PrefixList / Community / ExtendedCommunity
- QoSPolicy / TrafficClassifier / TrafficBehavior / PBR

### F. ServiceObject
- InternetAccessService / InterSitePrivateService / L3VPNService
- DCIService / TenantIsolationService / DualExitService / BackupService

### G. VerificationObject
- ReachabilityCheck / AdjacencyCheck / RouteTableCheck / TunnelCheck
- RedundancyCheck / NATSessionCheck / TrafficPathCheck

### 概念层关键关系
- `is_a` / `part_of` / `instance_of` / `connects_to` / `belongs_to`
- `uses_protocol` / `has_policy` / `provides_service` / `validated_by`

---

## 8.2 机制层（Mechanism Layer）

回答"为什么"。机制层是解释网络行为的动态语义单元，不是静态术语。

### A. RoutingMechanism
- LinkStateFlooding
- PathVectorPropagation
- BestPathSelection
- RecursiveNextHopResolution
- ECMPSelection
- RouteRedistribution
- DefaultRoutePropagation

### B. ForwardingMechanism
- LongestPrefixMatch
- LabelSwitching
- EncapsulationDecapsulation
- VxlanOverlayForwarding
- PolicyBasedForwarding

### C. RedundancyMechanism
- FirstHopRedundancy
- FastFailureDetection
- PrimaryBackupSwitchover
- ActiveStandbySelection
- LoadSharing

### D. IsolationMechanism
- VRFIsolation
- VlanIsolation
- RouteTargetBasedIsolation
- OverlayTenantIsolation
- ACLBasedIsolation

### E. TrafficControlMechanism
- ClassificationMarking
- QueueScheduling
- PolicingShaping
- CongestionAvoidance
- PreferenceManipulation

### F. ControlPlaneCoordinationMechanism
- NeighborAdjacencyFormation
- SessionEstablishment
- KeepaliveAndLiveness
- ReflectionAndReAdvertisement
- RouteImportExport

### 机制层关键关系
- `explains` / `depends_on` / `driven_by` / `involves_protocol`
- `affects` / `causes` / `enables` / `protects`

### 示例：BGP 的多层表达

在旧本体里，BGP 只是一个 ProtocolObject。在新结构里：
- `BGP` 仍存在于概念层；
- 关联的机制层对象包括：`SessionEstablishment` / `PathVectorPropagation` / `BestPathSelection` / `ReflectionAndReAdvertisement` / `RouteImportExport`

这样系统才能同时回答：BGP 是什么 → 为什么路由按某种方式传播 → 为什么某条路径被选中 → 为什么 RR 拓扑影响控制平面收敛。

---

## 8.3 方法层（Method Layer）

回答"怎么做"。方法层表达工程中的标准动作脚本与操作序列。

### A. DesignMethod
- RequirementDecompositionMethod
- CapabilityMappingMethod
- AddressPlanningMethod
- RoutingDomainPartitionMethod
- ExitStrategyDesignMethod
- TenantSegmentationDesignMethod

### B. ConfigurationMethod
- VRFProvisioningMethod
- PECEPeeringConfigurationMethod
- OSPFAreaDeploymentMethod
- BGPPolicyConfigurationMethod
- MPLSL3VPNProvisioningMethod
- EVPNVXLANProvisioningMethod
- DualExitConfigurationMethod
- QoSPolicyDeploymentMethod

### C. VerificationMethod
- NeighborVerificationMethod
- RouteVerificationMethod
- PathVerificationMethod
- FailoverVerificationMethod
- ServiceAcceptanceMethod
- ConsistencyVerificationMethod

### D. TroubleshootingMethod
- OSPFAdjacencyTroubleshootingMethod
- BGPSessionTroubleshootingMethod
- VPNReachabilityTroubleshootingMethod
- AsymmetricPathTroubleshootingMethod
- NATIssueTroubleshootingMethod

### E. ChangeMethod
- IncrementalDeploymentMethod
- MaintenanceWindowExecutionMethod
- RollbackMethod
- RiskIsolationMethod

### 方法层元属性

每个方法节点至少包含：

| 属性 | 说明 |
|------|------|
| input_objects | 输入对象 |
| output_objects | 输出对象 |
| preconditions | 前置条件 |
| execution_order | 执行顺序 |
| dependencies | 依赖对象 |
| verification_actions | 验证动作 |
| failure_handling | 失败处理 |
| applicable_scenarios | 适用场景 |

### 方法层关键关系
- `operates_on` / `produces` / `requires_precondition` / `precedes`
- `validated_by` / `used_in` / `mitigates`

---

## 8.4 条件层（Condition Layer）

回答"何时用、何时不用、为什么这样用"。这是从"知识点"迈向"工程判断"的关键层。

### A. ApplicabilityCondition
- SmallScaleApplicability
- LargeScaleApplicability
- MultiTenantApplicability
- DualExitApplicability
- CrossDomainApplicability
- LowLatencyApplicability

### B. ConstraintCondition
- DeviceCapabilityConstraint
- TeamOAMCapabilityConstraint
- AddressResourceConstraint
- ControlPlaneScaleConstraint
- HardwareFeatureConstraint
- InteroperabilityConstraint

### C. RiskCondition
- AsymmetricPathRisk
- RoutingLoopRisk
- RouteLeakRisk
- BroadcastDomainExpansionRisk
- FailoverOscillationRisk
- OperationalComplexityRisk

### D. DecisionRule
- PreferBGPOverStaticForScalabilityRule
- PreferVRFForIsolationRule
- AvoidLargeL2StretchRule
- PreferPolicyControlOverHardcodedFiltersRule
- PreferBFDForFastFailureRule
- PreferRouteReflectorForScaleRule

### E. ContraindicationRule
- AvoidRedistributionWithoutBoundaryControlRule
- AvoidDefaultRouteOnlyForGranularInterSitePolicyRule
- AvoidUnboundedEVPNFloodingRule
- AvoidVRRPLoadshareUnderCertainStatefulNATConditionsRule

### 条件层表达形式

- 规则表达式（IF-THEN）
- 决策表
- 约束关系
- 风险评分模型
- 适用性区间

示例：
- `IF 分支数量持续增长 AND 需统一策略控制 THEN 优先考虑 BGP/路由策略而非大量静态路由`
- `IF 业务要求广播域跨站点延伸 AND 规模较大 THEN 警惕二层扩展带来的广播与故障域风险`
- `IF 需亚秒级链路故障感知 THEN 引入 BFD 或等效快速检测机制`

### 条件层关键关系
- `applies_to` / `enables` / `limits` / `contraindicates`
- `preferred_under` / `risky_under` / `selected_by`

---

## 8.5 场景层（Scenario Layer）

回答"在什么业务背景下如何组合应用"。场景层是把概念、机制、方法、条件汇聚为工程模式的最高层。

### A. EnterpriseInterconnectionScenario
- HQBranchInterconnectScenario
- DualExitCampusInternetScenario
- BranchServiceSegmentationScenario
- MultiSitePrivateWANScenario

### B. VPNScenario
- MPLSL3VPNProvisioningScenario
- InterVRFCommunicationScenario
- ManagedCEAccessScenario

### C. DataCenterScenario
- EVPNVXLANFabricScenario
- MultiTenantDCIScenario
- L2ExtensionWithGatewayScenario
- SpineLeafUnderlayOverlayScenario

### D. RoutingCollaborationScenario
- OSPFToBGPBoundaryScenario
- RRScaleOutScenario
- DualUplinkConvergenceScenario
- PrimaryBackupRoutingScenario

### E. ChangeAndValidationScenario
- IncrementalMigrationScenario
- FailoverDrillScenario
- ServiceAcceptanceScenario
- TrafficPolicyAdjustmentScenario

### 场景层槽位定义

每个场景模式至少包含以下槽位：

| 槽位 | 说明 |
|------|------|
| business_goal | 业务目标 |
| network_scope | 网络边界与规模 |
| key_constraints | 关键约束 |
| concept_objects | 采用的概念对象 |
| key_mechanisms | 采用的关键机制 |
| required_methods | 所需方法脚本 |
| applicability_conditions | 适用条件 |
| contraindication_conditions | 禁忌条件 |
| verification_criteria | 验证与验收标准 |
| risks_and_rollback | 风险与回退 |
| case_references | 典型案例参考 |

### 示例：企业双出口园区场景

`DualExitCampusInternetScenario`：

- **业务目标**：互联网访问冗余、核心业务可用性、出口流量控制
- **关键对象**：边界路由器、防火墙、VRRP 网关、默认路由、NAT 策略、QoS 策略
- **关键机制**：FirstHopRedundancy、PrimaryBackupSwitchover、DefaultRoutePropagation、PolicyBasedForwarding
- **方法**：ExitStrategyDesignMethod、DualExitConfigurationMethod、FailoverVerificationMethod
- **适用条件**：双出口链路已就绪、防火墙支持主备会话同步
- **禁忌条件**：存在状态防火墙但不支持会话同步时，避免 VRRP 主备流量不对称
- **风险**：不对称路径、NAT 状态失配、主备抖动
- **验证**：主链路断开验证、路径验证、会话保持验证、业务恢复时间验证

---

# 9. 跨层关系链路设计

五层本体的关键不只是分层，而是跨层连通。

## 9.1 核心跨层关系

- Concept `participates_in` Mechanism
- Mechanism `implemented_by` Method
- Method `governed_by` ConditionRule
- Scenario `composed_of` Concept / Mechanism / Method / Condition
- Scenario `validated_by` VerificationMethod
- ConditionRule `selects` Method / Scenario
- ConditionRule `limits` Mechanism / Concept
- CaseNode `instantiates` ScenarioPattern

## 9.2 典型跨层链路

### 链路一：从概念到方法
```
VRF → RouteTargetBasedIsolation → VRFProvisioningMethod
```

### 链路二：从机制到条件
```
BestPathSelection → PreferBGPOverStaticForScalabilityRule
```

### 链路三：从场景到配置
```
DualExitCampusInternetScenario
  → ExitStrategyDesignMethod
  → DualExitConfigurationMethod
  → FailoverVerificationMethod
```

### 链路四：面向任务问答的知识召回链路
```
问题："某企业双出口园区如何做主备切换？"
→ 场景层召回 DualExitCampusInternetScenario
→ 条件层过滤适用模式
→ 方法层返回配置与验证脚本
→ 概念与机制层提供解释与证据
```

---

# 10. 标签体系

本体承担稳定的主标签体系，v0.2 扩展为五类语义标签。

## 10.1 多维标签体系

每个知识片段至少支持以下五类标签，使同一段文本可以同时跨层索引：

| 标签类型 | 示例 |
|---------|------|
| `concept_tags` | BGP, VRF, OSPF |
| `mechanism_tags` | BestPathSelection, RouteTargetBasedIsolation |
| `method_tags` | BGPPolicyConfigurationMethod, VRFProvisioningMethod |
| `condition_tags` | PreferBGPOverStaticForScalabilityRule, AsymmetricPathRisk |
| `scenario_tags` | MPLSL3VPNProvisioningScenario, DualExitCampusInternetScenario |
| `semantic_role_tags` | 定义 / 机制 / 约束 / 配置 / 故障 / 排障 / 最佳实践 |

## 10.2 Canonical Tag

每个 Canonical Tag 对应一个本体节点（概念层）：

- `BGP` / `OSPF` / `EVPN` / `OTN` / `AMF` / `OLT` 等

## 10.3 Context Tag（非本体）

以下标签不进入本体主干，由独立词表管理：

- 园区网 / 承载网 / 数据中心 / 接入网 / 城域网 / 5GC / 多厂商组网

---

# 11. 节点属性规范

## 11.1 概念节点属性（ConceptNode）

| 属性 | 说明 |
|------|------|
| id | 节点唯一标识（如 IP.BGP） |
| canonical_name | 规范名称 |
| display_name_zh | 中文名 |
| knowledge_layer | concept |
| domain | 所属一级域 |
| parent_id | 父节点 ID |
| aliases | 别名列表 |
| description | 简要描述 |
| scope_note | 使用范围说明 |
| examples | 示例 |
| allowed_relations | 允许的关系类型 |
| maturity_level | core / standard / experimental |
| source_basis | 来源标准 |
| lifecycle_state | active / deprecated |
| version_introduced | 引入版本 |

## 11.2 机制节点属性（MechanismNode）

| 属性 | 说明 |
|------|------|
| id | 节点唯一标识 |
| canonical_name | 规范名称 |
| knowledge_layer | mechanism |
| involved_concepts | 关联的概念层对象 |
| causal_chain | 因果链描述 |
| failure_modes | 相关故障模式 |
| source_basis | 来源 |

## 11.3 方法节点属性（MethodNode）

| 属性 | 说明 |
|------|------|
| id | 节点唯一标识 |
| canonical_name | 规范名称 |
| knowledge_layer | method |
| input_objects | 输入对象 |
| output_objects | 输出对象 |
| preconditions | 前置条件 |
| execution_steps | 执行步骤（有序列表） |
| verification_actions | 验证动作 |
| failure_handling | 失败处理 |
| applicable_scenarios | 适用场景 |

## 11.4 条件规则节点属性（ConditionRuleNode）

| 属性 | 说明 |
|------|------|
| id | 节点唯一标识 |
| canonical_name | 规范名称 |
| knowledge_layer | condition |
| rule_type | applicability / constraint / risk / decision / contraindication |
| condition_expression | 条件表达式（IF-THEN 或自然语言） |
| applies_to | 约束对象 |
| risk_level | 风险等级（若适用） |

## 11.5 场景模式节点属性（ScenarioPatternNode）

| 属性 | 说明 |
|------|------|
| id | 节点唯一标识 |
| canonical_name | 规范名称 |
| knowledge_layer | scenario |
| business_goal | 业务目标 |
| network_scope | 网络边界与规模 |
| concept_objects | 采用的概念对象 |
| key_mechanisms | 关键机制 |
| required_methods | 所需方法 |
| conditions | 适用与禁忌条件 |
| verification_criteria | 验证标准 |
| risks_and_rollback | 风险与回退 |

---

# 12. 命名与标识规范

## 12.1 命名原则

- 优先使用领域内通行 canonical 名称
- 中文名和英文名同时维护
- 避免将临时简称直接作为主名
- 避免厂商私有术语污染标准概念层

## 12.2 节点 ID 规范

| 层 | ID 前缀示例 |
|----|------------|
| 概念层 | `IP.BGP` / `OPTICAL.OTN` / `MOBILE.AMF` |
| 机制层 | `MECH.BestPathSelection` / `MECH.VRFIsolation` |
| 方法层 | `METHOD.VRFProvisioningMethod` / `METHOD.RouteVerificationMethod` |
| 条件层 | `COND.PreferBGPOverStaticRule` / `COND.AsymmetricPathRisk` |
| 场景层 | `SCENE.DualExitCampusInternetScenario` / `SCENE.MPLSL3VPNProvisioningScenario` |

---

# 13. 词汇层设计

词汇层用于承接本体之外的语言变化，不进入核心知识层。

## 13.1 Alias
- Border Gateway Protocol → BGP
- Interior Gateway Protocol → IGP

## 13.2 Vendor Term
厂商私有命名映射至 canonical 概念。

## 13.3 Abbreviation
缩写与简称单独维护。

## 13.4 Surface Form
文档中的原始词面表达。

---

# 14. 候选概念层设计

候选概念层承接尚未正式进入本体的新知识，五层均有对应的候选状态。

## 14.1 候选来源

- 高频新术语
- 多源一致但未命中的概念
- 关系抽取中反复出现的新对象
- 新标准引入的新机制/方法

## 14.2 候选字段

- candidate_id / surface_forms / candidate_layer / candidate_parent
- source_count / source_diversity / temporal_stability
- structural_fit / retrieval_gain / synonym_risk / review_status

## 14.3 候选流转状态

- discovered → normalized → clustered → scored → pending_review → accepted / rejected / downgraded_to_alias

---

# 15. 本体演化规则

## 15.1 可自动更新的层

- Alias / 缩写 / 词面表达 / 厂商术语映射

## 15.2 仅可半自动更新的层

- 子域概念层（新协议/设备对象）
- 子域机制层补充
- 条件层新规则（需人工审核逻辑）

## 15.3 仅人工审批的层

- 顶层概念
- 关系类型体系
- 核心域骨架
- 场景层新增模式

## 15.4 入本体条件

### 概念层
候选概念需满足：多个高质量来源出现、时间上持续存在、能接入明确父节点、与已有节点非简单同义、对检索或推理有明显增益。

### 机制/方法/条件/场景层（新增）

新知识对象还需满足：
- 新机制：是否值得单独建模（与现有机制有实质区别）
- 新方法：是否形成可复用脚本（不是一次性操作）
- 新条件：是否形成稳定规则（在多个案例中验证）
- 新场景：是否形成可复用模式（不是单次工程案例）

---

# 16. 约束与一致性规则

## 16.1 结构约束

- 每个正式概念节点必须有父节点
- 不允许孤立核心概念
- 同层粒度应基本一致

## 16.2 关系约束

- 关系谓词必须来自受控关系集合（层内或跨层）
- 不同知识对象类型允许的关系不同
- 跨层关系方向不可反转（如 Mechanism 不能 `participates_in` Concept）
- 非法边必须在治理阶段拦截

## 16.3 命名约束

- 同一 canonical 概念只能有一个主名
- 别名不能反向形成多个 canonical 主节点
- 禁止重复概念节点

---

# 17. 知识抽取流水线对接

五层本体要求抽取流水线从"实体关系抽取"升级为"多层知识对象抽取"。

## 17.1 抽取目标映射

| 抽取任务 | 目标层 |
|---------|--------|
| 识别概念对象（协议、设备、接口） | 概念层 |
| 识别机制描述（工作原理、状态迁移、因果链） | 机制层 |
| 识别方法脚本片段（配置步骤、验证流程） | 方法层 |
| 识别条件句与决策规则（适用条件、禁忌、约束） | 条件层 |
| 识别场景背景（业务目标、组网模式、案例） | 场景层 |

## 17.2 知识来源双通道策略

- **公共语料通道**：从公开文档沉淀概念层、机制层、部分方法层
- **工程归纳通道**：从案例、规则、模板、专家建模沉淀条件层、场景层、方法模板

## 17.3 标签挂载策略

每个知识片段在入库时，需同时为五类标签打标：

```
concept_tags: [BGP, VRF]
mechanism_tags: [PathVectorPropagation, RouteImportExport]
method_tags: [VRFProvisioningMethod]
condition_tags: [PreferVRFForIsolationRule]
scenario_tags: [MPLSL3VPNProvisioningScenario]
```

---

# 18. 本体文件组织方式

```text
ontology/
  top/
    entities.yaml           ← 顶层实体类
    behaviors.yaml          ← 顶层行为类
    rules.yaml              ← 顶层规则类
    relations.yaml          ← 受控关系类型（含跨层关系）
    states.yaml             ← 状态类
  domains/
    physical.yaml
    access.yaml
    ip_network/
      concepts.yaml         ← 概念层（数通域）
      mechanisms.yaml       ← 机制层（数通域）
      methods.yaml          ← 方法层（数通域）
      conditions.yaml       ← 条件层（数通域）
      scenarios.yaml        ← 场景层（数通域）
    optical.yaml
    transport.yaml
    mobile_core.yaml
    datacenter.yaml
    management_oam.yaml
    security.yaml
    service_business.yaml
    operations_fault.yaml
    config_automation.yaml
  lexicon/
    aliases.yaml
    abbreviations.yaml
    vendor_terms.yaml
  governance/
    evolution_policy.yaml
    constraints.yaml
    naming_rules.yaml
  versions/
    ontology_v0.1.0.json
    ontology_v0.2.0.json
```

---

# 19. YAML 节点示例

## 19.1 概念节点示例

```yaml
id: IP.BGP
canonical_name: BGP
display_name_zh: 边界网关协议
knowledge_layer: concept
domain: IP / Data Communication Network
parent_id: IP.ROUTING_PROTOCOL
aliases:
  - Border Gateway Protocol
description: 一种路径矢量路由协议，用于自治系统间和大规模网络中的路由交换。
allowed_relations:
  - uses_protocol
  - advertises
  - depends_on
  - configured_by
  - supported_by
  - participates_in
maturity_level: core
source_basis:
  - IETF RFC 4271
lifecycle_state: active
version_introduced: v0.1.0
```

## 19.2 机制节点示例

```yaml
id: MECH.BestPathSelection
canonical_name: BestPathSelection
display_name_zh: 最优路径选择
knowledge_layer: mechanism
involved_concepts:
  - IP.BGP
  - IP.OSPF
causal_chain: >
  BGP 收到多条路由时，按照 Weight → LocalPref → AS-Path 长度 → Origin →
  MED → eBGP/iBGP → IGP Metric 等属性依次比较，选出最优路由安装到路由表。
failure_modes:
  - 路由不对称（两端选路结果不一致）
  - LocalPref 配置不一致导致出口选路错误
explains:
  - IP.BGP
source_basis:
  - IETF RFC 4271 Section 9.1
```

## 19.3 场景节点示例

```yaml
id: SCENE.DualExitCampusInternetScenario
canonical_name: DualExitCampusInternetScenario
display_name_zh: 企业双出口园区互联网接入场景
knowledge_layer: scenario
business_goal: 互联网访问冗余、核心业务可用性、出口流量控制
network_scope: 单园区、双 ISP 链路、边界防火墙
concept_objects:
  - IP.VRRP
  - IP.BGP
  - IP.NAT
  - IP.ACL
key_mechanisms:
  - MECH.FirstHopRedundancy
  - MECH.PrimaryBackupSwitchover
  - MECH.DefaultRoutePropagation
required_methods:
  - METHOD.ExitStrategyDesignMethod
  - METHOD.DualExitConfigurationMethod
  - METHOD.FailoverVerificationMethod
conditions:
  applicable:
    - COND.DualExitApplicability
  contraindicated:
    - COND.AvoidVRRPLoadshareUnderCertainStatefulNATConditionsRule
verification_criteria:
  - 主链路断开后 < 1s 完成主备切换
  - NAT 会话保持率 > 95%
risks_and_rollback:
  - 不对称路径风险：需检查回流路由
  - 主备抖动：配置 VRRP 抢占延迟
```

---

# 20. 本体质量评估建议

## 20.1 评估维度

### v0.1 继承维度
- 覆盖度（概念节点数与领域参考协议数之比）
- 层次一致性
- 关系合法性
- 别名归一质量
- 检索增益
- 演化稳定性

### v0.2 新增维度
- 机制覆盖率（核心协议是否均有机制层建模）
- 方法覆盖率（核心操作是否有方法层对象）
- 条件规则覆盖率（关键决策是否有显式规则）
- 场景覆盖率（典型业务场景是否有完整模式）
- **跨层可连通性**（场景→方法→机制→概念链路是否完整）

## 20.2 面向任务闭环评测

对于每个核心场景，检查是否可完整支持：

1. 场景识别
2. 关键概念召回
3. 机制解释
4. 方法输出
5. 条件筛选
6. 验证路径输出

## 20.3 知识槽位完整性评测

以 `MPLSL3VPNProvisioningScenario` 为例，检查以下槽位是否填充：
- 业务目标 / 关键对象 / 机制 / 方法 / 条件 / 风险 / 验证

若场景存在但只填了概念与定义，则说明它仍停留在"概念本体"阶段，未达到工程语义本体标准。

## 20.4 评估方法

- 专家抽检
- 典型问答集映射测试（按五类检索入口各设测试用例）
- 事实抽取对齐测试
- 子域增量扩展测试
- 演化回归测试

---

# 21. 结论

本体设计的核心思想（v0.2）：

1. **用五层语义结构统一知识组织**：概念（是什么）→ 机制（为什么）→ 方法（怎么做）→ 条件（何时用）→ 场景（在什么业务背景下组合应用）；
2. **用顶层稳定抽象统一通信领域语义骨架**；
3. **用一级域和子域承接具体通信知识**，以 IP/数通域为首个深挖方向；
4. **用词汇层承接高频变化的语言表达**；
5. **用候选概念层承接新知识而不污染核心本体**；
6. **用受控关系体系（含跨层关系）保证知识结构可计算、可约束、可演化**；
7. **知识评测从"概念覆盖率"升级为"任务闭环覆盖率"**。

条件层与场景层将成为区分"百科知识库"和"工程知识基础设施"的关键。在工程实施中，建议先以 IP/数通子域作为最小实验单元，建立高质量五层本体与知识入库闭环，再逐步扩展到光网、接入网、核心网、运维故障和自动化配置等领域。