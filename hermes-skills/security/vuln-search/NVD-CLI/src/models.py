"""
数据模型模块

定义 NVD API 响应的 Pydantic 模型。
本模块只负责数据结构定义与校验，不包含任何业务逻辑或 I/O 操作，
确保与 HTTP 客户端、格式化器等模块完全解耦。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ======================================================================
# CVSS 相关模型
# ======================================================================


class CVSSv2Data(BaseModel):
    """CVSS v2 向量与评分数据"""

    version: str = ""
    vector_string: str = Field("", alias="vectorString")
    access_vector: str = Field("", alias="accessVector")
    access_complexity: str = Field("", alias="accessComplexity")
    authentication: str = Field("", alias="authentication")
    confidentiality_impact: str = Field("", alias="confidentialityImpact")
    integrity_impact: str = Field("", alias="integrityImpact")
    availability_impact: str = Field("", alias="availabilityImpact")
    base_score: float = Field(0.0, alias="baseScore")

    model_config = {"populate_by_name": True}


class CVSSv2Metric(BaseModel):
    """单条 CVSS v2 评估记录"""

    source: str = ""
    type: str = ""
    cvss_data: CVSSv2Data = Field(default_factory=CVSSv2Data, alias="cvssData")
    base_severity: str = Field("", alias="baseSeverity")
    exploitability_score: float | None = Field(None, alias="exploitabilityScore")
    impact_score: float | None = Field(None, alias="impactScore")

    model_config = {"populate_by_name": True}


class CVSSv3Data(BaseModel):
    """CVSS v3 向量与评分数据"""

    version: str = ""
    vector_string: str = Field("", alias="vectorString")
    attack_vector: str = Field("", alias="attackVector")
    attack_complexity: str = Field("", alias="attackComplexity")
    privileges_required: str = Field("", alias="privilegesRequired")
    user_interaction: str = Field("", alias="userInteraction")
    scope: str = ""
    confidentiality_impact: str = Field("", alias="confidentialityImpact")
    integrity_impact: str = Field("", alias="integrityImpact")
    availability_impact: str = Field("", alias="availabilityImpact")
    base_score: float = Field(0.0, alias="baseScore")
    base_severity: str = Field("", alias="baseSeverity")

    model_config = {"populate_by_name": True}


class CVSSv3Metric(BaseModel):
    """单条 CVSS v3 评估记录"""

    source: str = ""
    type: str = ""
    cvss_data: CVSSv3Data = Field(default_factory=CVSSv3Data, alias="cvssData")
    exploitability_score: float | None = Field(None, alias="exploitabilityScore")
    impact_score: float | None = Field(None, alias="impactScore")

    model_config = {"populate_by_name": True}


class CVSSv4Data(BaseModel):
    """CVSS v4 向量与评分数据"""

    version: str = ""
    vector_string: str = Field("", alias="vectorString")
    base_score: float = Field(0.0, alias="baseScore")
    base_severity: str = Field("", alias="baseSeverity")

    model_config = {"populate_by_name": True}


class CVSSv4Metric(BaseModel):
    """单条 CVSS v4 评估记录"""

    source: str = ""
    type: str = ""
    cvss_data: CVSSv4Data = Field(default_factory=CVSSv4Data, alias="cvssData")

    model_config = {"populate_by_name": True}


class Metrics(BaseModel):
    """CVE 影响评估指标集合，可包含 v2/v3/v4 中的任意组合"""

    cvss_metric_v2: list[CVSSv2Metric] = Field(default_factory=list, alias="cvssMetricV2")
    cvss_metric_v31: list[CVSSv3Metric] = Field(default_factory=list, alias="cvssMetricV31")
    cvss_metric_v30: list[CVSSv3Metric] = Field(default_factory=list, alias="cvssMetricV30")
    cvss_metric_v4: list[CVSSv4Metric] = Field(default_factory=list, alias="cvssMetricV40")

    model_config = {"populate_by_name": True}

    def best_score(self) -> tuple[float, str]:
        """
        返回最高版本的 CVSS 评分和严重度。

        优先级: v4 > v3.1 > v3.0 > v2

        Returns:
            (base_score, severity) 元组；无数据时返回 (0.0, "N/A")
        """
        if self.cvss_metric_v4:
            m = self.cvss_metric_v4[0]
            return m.cvss_data.base_score, m.cvss_data.base_severity
        if self.cvss_metric_v31:
            m = self.cvss_metric_v31[0]
            return m.cvss_data.base_score, m.cvss_data.base_severity
        if self.cvss_metric_v30:
            m = self.cvss_metric_v30[0]
            return m.cvss_data.base_score, m.cvss_data.base_severity
        if self.cvss_metric_v2:
            m = self.cvss_metric_v2[0]
            return m.cvss_data.base_score, m.base_severity
        return 0.0, "N/A"


# ======================================================================
# 描述、弱点、引用等辅助模型
# ======================================================================


class Description(BaseModel):
    """CVE 描述文本，含语言标识"""

    lang: str = "en"
    value: str = ""


class Weakness(BaseModel):
    """CWE 弱点信息"""

    source: str = ""
    type: str = ""
    description: list[Description] = Field(default_factory=list)


class CPEMatch(BaseModel):
    """CPE 匹配条目"""

    vulnerable: bool = True
    criteria: str = ""
    match_criteria_id: str = Field("", alias="matchCriteriaId")
    version_start: str | None = Field(None, alias="versionStart")
    version_start_including: str | None = Field(None, alias="versionStartIncluding")
    version_end: str | None = Field(None, alias="versionEnd")
    version_end_including: str | None = Field(None, alias="versionEndIncluding")

    model_config = {"populate_by_name": True}


class Node(BaseModel):
    """配置节点，包含操作符与 CPE 匹配列表"""

    operator: str = "OR"
    negate: bool = False
    cpe_match: list[CPEMatch] = Field(default_factory=list, alias="cpeMatch")

    model_config = {"populate_by_name": True}


class Configuration(BaseModel):
    """CVE 适用性声明（受影响产品配置）"""

    nodes: list[Node] = Field(default_factory=list)


class Reference(BaseModel):
    """CVE 参考链接"""

    url: str = ""
    source: str = ""
    tags: list[str] = Field(default_factory=list)


class VendorComment(BaseModel):
    """厂商官方评论"""

    organization: str = ""
    comment: str = ""
    last_modified: str = Field("", alias="lastModified")

    model_config = {"populate_by_name": True}


class CVETag(BaseModel):
    """CVE 标签（如 disputed、unsupported-when-assigned）"""

    source_identifier: str = Field("", alias="sourceIdentifier")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class AffectedVersion(BaseModel):
    """受影响版本条目"""

    version: str = ""
    status: str = ""


class AffectedProduct(BaseModel):
    """受影响产品信息"""

    vendor: str = ""
    product: str = ""
    versions: list[AffectedVersion] = Field(default_factory=list)


class AffectedData(BaseModel):
    """受影响数据来源"""

    source: str = ""
    affected_data: list[AffectedProduct] = Field(default_factory=list, alias="affectedData")

    model_config = {"populate_by_name": True}


# ======================================================================
# CVE 核心模型
# ======================================================================


class CVE(BaseModel):
    """
    单条 CVE 记录的完整模型。

    对应 NVD CVE API 响应中 vulnerabilities[].cve 的结构。
    所有可选字段使用默认值，确保即使 API 返回不完整数据也不会解析失败。
    """

    id: str = Field("", alias="cveId")
    source_identifier: str = Field("", alias="sourceIdentifier")
    published: str = ""
    last_modified: str = Field("", alias="lastModified")
    vuln_status: str = Field("", alias="vulnStatus")

    # CISA KEV 相关字段
    cisa_exploit_add: str | None = Field(None, alias="cisaExploitAdd")
    cisa_action_due: str | None = Field(None, alias="cisaActionDue")
    cisa_required_action: str | None = Field(None, alias="cisaRequiredAction")
    cisa_vulnerability_name: str | None = Field(None, alias="cisaVulnerabilityName")

    # 可选内容块
    cve_tags: list[CVETag] = Field(default_factory=list, alias="cveTags")
    descriptions: list[Description] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    weaknesses: list[Weakness] = Field(default_factory=list)
    configurations: list[Configuration] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    vendor_comments: list[VendorComment] = Field(default_factory=list, alias="vendorComments")
    affected: list[AffectedData] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def en_description(self) -> str:
        """获取英文描述文本；无英文描述时返回第一条。"""
        for d in self.descriptions:
            if d.lang == "en":
                return d.value
        return self.descriptions[0].value if self.descriptions else ""

    def cwe_ids(self) -> list[str]:
        """提取所有 CWE ID 列表。"""
        result: list[str] = []
        for w in self.weaknesses:
            for desc in w.description:
                if desc.value and desc.value.startswith("CWE-"):
                    result.append(desc.value)
        return result


# ======================================================================
# API 响应包装模型
# ======================================================================


class CVEResponse(BaseModel):
    """
    CVE API 的完整响应结构。

    包含分页信息和 CVE 列表。
    """

    results_per_page: int = Field(0, alias="resultsPerPage")
    start_index: int = Field(0, alias="startIndex")
    total_results: int = Field(0, alias="totalResults")
    format: str = ""
    version: str = ""
    timestamp: str = ""
    vulnerabilities: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def parse_cves(self) -> list[CVE]:
        """
        将原始 vulnerabilities 列表解析为 CVE 模型列表。

        单独提供此方法而非用嵌套模型，是为了在单条 CVE 解析失败时
        不影响其余记录，增强容错性。

        Returns:
            成功解析的 CVE 列表
        """
        result: list[CVE] = []
        for item in self.vulnerabilities:
            try:
                cve_data = item.get("cve", item)
                result.append(CVE.model_validate(cve_data))
            except Exception:
                continue
        return result


# ======================================================================
# CVE 变更历史模型
# ======================================================================


class ChangeDetail(BaseModel):
    """单条变更详情"""

    action: str = ""
    type: str = ""
    old_value: str = Field("", alias="oldValue")
    new_value: str = Field("", alias="newValue")

    model_config = {"populate_by_name": True}


class CVEChange(BaseModel):
    """单条 CVE 变更记录"""

    cve_id: str = Field("", alias="cveId")
    event_name: str = Field("", alias="eventName")
    cve_change_id: str = Field("", alias="cveChangeId")
    source_identifier: str = Field("", alias="sourceIdentifier")
    created: str = ""
    details: list[ChangeDetail] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CVEHistoryResponse(BaseModel):
    """CVE Change History API 的完整响应结构"""

    results_per_page: int = Field(0, alias="resultsPerPage")
    start_index: int = Field(0, alias="startIndex")
    total_results: int = Field(0, alias="totalResults")
    format: str = ""
    version: str = ""
    timestamp: str = ""
    cve_changes: list[dict[str, Any]] = Field(default_factory=list, alias="cveChanges")

    model_config = {"populate_by_name": True}

    def parse_changes(self) -> list[CVEChange]:
        """
        将原始 cveChanges 列表解析为 CVEChange 模型列表。

        Returns:
            成功解析的 CVEChange 列表
        """
        result: list[CVEChange] = []
        for item in self.cve_changes:
            try:
                change_data = item.get("change", item)
                result.append(CVEChange.model_validate(change_data))
            except Exception:
                continue
        return result
