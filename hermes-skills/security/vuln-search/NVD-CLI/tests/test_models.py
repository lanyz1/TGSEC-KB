"""
Pydantic 数据模型测试
"""

import pytest

from models import (
    CVE, CVEResponse, CVEChange, CVEHistoryResponse,
    CVSSv2Data, CVSSv2Metric, CVSSv3Data, CVSSv3Metric,
    CVSSv4Data, CVSSv4Metric, Metrics, Description, Weakness,
    CPEMatch, Node, Configuration, Reference, ChangeDetail,
)


class TestMetricsBestScore:
    """Metrics.best_score() 优先级测试"""

    def test_empty_metrics_returns_zero(self):
        m = Metrics()
        assert m.best_score() == (0.0, "N/A")

    def test_v2_only(self):
        m = Metrics(cvss_metric_v2=[
            CVSSv2Metric(cvss_data=CVSSv2Data(baseScore=7.5), baseSeverity="HIGH")
        ])
        score, severity = m.best_score()
        assert score == 7.5
        assert severity == "HIGH"

    def test_v3_takes_priority_over_v2(self):
        m = Metrics(
            cvss_metric_v2=[
                CVSSv2Metric(cvss_data=CVSSv2Data(baseScore=5.0), baseSeverity="MEDIUM")
            ],
            cvss_metric_v31=[
                CVSSv3Metric(cvss_data=CVSSv3Data(baseScore=9.8, baseSeverity="CRITICAL"))
            ],
        )
        score, severity = m.best_score()
        assert score == 9.8
        assert severity == "CRITICAL"

    def test_v4_takes_priority_over_v3(self):
        m = Metrics(
            cvss_metric_v31=[
                CVSSv3Metric(cvss_data=CVSSv3Data(baseScore=7.5, baseSeverity="HIGH"))
            ],
            cvss_metric_v4=[
                CVSSv4Metric(cvss_data=CVSSv4Data(baseScore=8.5, baseSeverity="HIGH"))
            ],
        )
        score, severity = m.best_score()
        assert score == 8.5

    def test_v31_takes_priority_over_v30(self):
        m = Metrics(
            cvss_metric_v30=[
                CVSSv3Metric(cvss_data=CVSSv3Data(baseScore=5.0, baseSeverity="MEDIUM"))
            ],
            cvss_metric_v31=[
                CVSSv3Metric(cvss_data=CVSSv3Data(baseScore=10.0, baseSeverity="CRITICAL"))
            ],
        )
        score, severity = m.best_score()
        assert score == 10.0


class TestCVE:
    """CVE 模型测试"""

    def test_parse_with_alias(self):
        cve = CVE.model_validate({
            "cveId": "CVE-2024-3094",
            "sourceIdentifier": "<EMAIL-REDACTED>",
            "vulnStatus": "Analyzed",
        })
        assert cve.id == "CVE-2024-3094"
        assert cve.source_identifier == "<EMAIL-REDACTED>"
        assert cve.vuln_status == "Analyzed"

    def test_default_values(self):
        cve = CVE()
        assert cve.id == ""
        assert cve.descriptions == []
        assert cve.metrics.cvss_metric_v2 == []

    def test_en_description_english(self):
        cve = CVE(descriptions=[
            Description(lang="en", value="English desc"),
            Description(lang="es", value="Spanish desc"),
        ])
        assert cve.en_description() == "English desc"

    def test_en_description_fallback(self):
        cve = CVE(descriptions=[
            Description(lang="es", value="Spanish desc"),
        ])
        assert cve.en_description() == "Spanish desc"

    def test_en_description_empty(self):
        cve = CVE()
        assert cve.en_description() == ""

    def test_cwe_ids(self):
        cve = CVE(weaknesses=[
            Weakness(description=[Description(value="CWE-79")]),
            Weakness(description=[Description(value="CWE-89")]),
        ])
        assert cve.cwe_ids() == ["CWE-79", "CWE-89"]

    def test_cwe_ids_filters_non_cwe(self):
        cve = CVE(weaknesses=[
            Weakness(description=[Description(value="CWE-79"), Description(value="NVD-CWE-Other")]),
        ])
        assert cve.cwe_ids() == ["CWE-79"]

    def test_cisa_kev_fields(self):
        cve = CVE.model_validate({
            "cveId": "CVE-2021-44228",
            "cisaExploitAdd": "2021-12-10",
            "cisaRequiredAction": "Apply updates",
            "cisaVulnerabilityName": "Log4Shell",
        })
        assert cve.cisa_exploit_add == "2021-12-10"
        assert cve.cisa_required_action == "Apply updates"


class TestCVEResponse:
    """CVEResponse 解析测试"""

    def test_parse_cves_success(self):
        resp = CVEResponse.model_validate({
            "resultsPerPage": 1,
            "startIndex": 0,
            "totalResults": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "cveId": "CVE-2024-3094",
                        "vulnStatus": "Analyzed",
                    }
                }
            ],
        })
        cves = resp.parse_cves()
        assert len(cves) == 1
        assert cves[0].id == "CVE-2024-3094"

    def test_parse_cves_skips_invalid(self):
        resp = CVEResponse.model_validate({
            "resultsPerPage": 2,
            "vulnerabilities": [
                {"cve": {"cveId": "CVE-2024-3094"}},
                {"cve": None},
            ],
        })
        cves = resp.parse_cves()
        assert len(cves) == 1

    def test_parse_cves_empty(self):
        resp = CVEResponse()
        assert resp.parse_cves() == []


class TestCVEChange:
    """CVEChange 模型测试"""

    def test_parse_with_alias(self):
        ch = CVEChange.model_validate({
            "cveId": "CVE-2024-3094",
            "eventName": "CVE Modified",
            "cveChangeId": "change-123",
            "sourceIdentifier": "<EMAIL-REDACTED>",
            "created": "2024-03-29T10:00:00",
        })
        assert ch.cve_id == "CVE-2024-3094"
        assert ch.event_name == "CVE Modified"

    def test_details_parsed(self):
        ch = CVEChange.model_validate({
            "cveId": "CVE-2024-3094",
            "eventName": "Initial Analysis",
            "details": [
                {"action": "Added", "type": "description", "newValue": "Initial"},
            ],
        })
        assert len(ch.details) == 1
        assert ch.details[0].action == "Added"


class TestCVEHistoryResponse:
    """CVEHistoryResponse 解析测试"""

    def test_parse_changes(self):
        resp = CVEHistoryResponse.model_validate({
            "resultsPerPage": 1,
            "totalResults": 1,
            "cveChanges": [
                {
                    "change": {
                        "cveId": "CVE-2024-3094",
                        "eventName": "CVE Modified",
                    }
                }
            ],
        })
        changes = resp.parse_changes()
        assert len(changes) == 1
        assert changes[0].cve_id == "CVE-2024-3094"


class TestCPEMatch:
    """CPEMatch 模型测试"""

    def test_parse_with_alias(self):
        m = CPEMatch.model_validate({
            "criteria": "cpe:2.3:a:apache:log4j:2.0:*:*:*:*:*:*:*",
            "matchCriteriaId": "abc-123",
            "vulnerable": True,
        })
        assert m.criteria.startswith("cpe:2.3")
        assert m.vulnerable is True


class TestConfiguration:
    """Configuration 嵌套模型测试"""

    def test_nested_parse(self):
        cfg = Configuration.model_validate({
            "nodes": [
                {
                    "operator": "OR",
                    "cpeMatch": [
                        {"criteria": "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*", "vulnerable": True}
                    ]
                }
            ]
        })
        assert len(cfg.nodes) == 1
        assert len(cfg.nodes[0].cpe_match) == 1
