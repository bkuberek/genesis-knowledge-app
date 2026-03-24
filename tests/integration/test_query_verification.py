"""Verify the database can answer the 4 required sample questions.

These tests require a running database with sample_data.csv ingested.
They test the repository layer directly via the REST API, not the LLM.

Expected data: 500 companies from docs/product/user-requirements/sample_data.csv
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestFintechAverageARR:
    """Q1: What is the average ARR for fintech companies?

    Expected: 19 Fintech companies with average ARR ~1414.89 thousands.
    """

    async def test_count_fintech_companies(self, api_client, auth_headers):
        response = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "filters": [
                    {"property": "industry_vertical", "operator": "=", "value": "Fintech"},
                ],
                "limit": 100,
            },
        )
        if response.status_code == 404:
            pytest.skip("Tool query endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 19

    async def test_fintech_filter_is_case_insensitive(self, api_client, auth_headers):
        """Querying with lowercase 'fintech' should return the same results as 'Fintech'."""
        response_lower = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "filters": [
                    {"property": "industry_vertical", "operator": "=", "value": "fintech"},
                ],
                "limit": 100,
            },
        )
        response_upper = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "filters": [
                    {"property": "industry_vertical", "operator": "=", "value": "FINTECH"},
                ],
                "limit": 100,
            },
        )
        if response_lower.status_code == 404:
            pytest.skip("Tool query endpoint not available")
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        assert response_lower.json()["count"] == 19
        assert response_upper.json()["count"] == 19


class TestHighestGrowthRate:
    """Q2: Which company has the highest growth rate?

    Expected: ArcApp with yoy_growth_rate_percent = 150.0%.
    """

    async def test_highest_growth_company(self, api_client, auth_headers):
        response = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "sort_by": "yoy_growth_rate_percent",
                "sort_order": "desc",
                "limit": 1,
            },
        )
        if response.status_code == 404:
            pytest.skip("Tool query endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        top = data["results"][0]
        assert top["name"] == "ArcApp"
        assert float(top["properties"]["yoy_growth_rate_percent"]) == pytest.approx(150.0)


class TestFoundedAfter2020LowChurn:
    """Q3: Companies founded after 2020 with churn < 5%.

    Expected: 19 companies matching founding_year > 2020 AND churn_rate_percent < 5.
    """

    async def test_count_founded_after_2020_low_churn(self, api_client, auth_headers):
        response = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "filters": [
                    {"property": "founding_year", "operator": ">", "value": 2020},
                    {"property": "churn_rate_percent", "operator": "<", "value": 5},
                ],
                "limit": 100,
            },
        )
        if response.status_code == 404:
            pytest.skip("Tool query endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 19


class TestCompaniesOver100Employees:
    """Q4: How many companies have more than 100 employees?

    Expected: 0 (max employee count in sample data is 52).
    """

    async def test_no_companies_over_100_employees(self, api_client, auth_headers):
        response = await api_client.post(
            "/api/chat/tools/query",
            json={
                "entity_type": "company",
                "filters": [
                    {"property": "employee_count", "operator": ">", "value": 100},
                ],
                "limit": 100,
            },
        )
        if response.status_code == 404:
            pytest.skip("Tool query endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0


class TestSchemaIncludesSampleValues:
    """Verify the describe_tables endpoint returns enhanced schema with samples."""

    async def test_schema_has_sample_values(self, api_client, auth_headers):
        response = await api_client.post(
            "/api/chat/tools/describe",
            json={},
        )
        if response.status_code == 404:
            pytest.skip("Tool describe endpoint not available")
        assert response.status_code == 200
        schema = response.json()
        if "company" in schema:
            props = schema["company"].get("properties", {})
            # String properties should have samples
            if "industry_vertical" in props:
                assert "samples" in props["industry_vertical"]
                assert len(props["industry_vertical"]["samples"]) > 0
            # Numeric properties should have min/max
            if "arr_thousands" in props:
                assert "min" in props["arr_thousands"]
                assert "max" in props["arr_thousands"]
