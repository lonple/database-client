from dbc_askdata.tools.gateway import build_column_profile


def test_build_column_profile_enum_like():
    stats = {
        "statements": [
            {
                "success": True,
                "rows": [[150, 2, 5]],
                "columns": [{"name": "cnt"}, {"name": "distinct_cnt"}, {"name": "null_cnt"}],
            }
        ]
    }
    values = {
        "statements": [
            {
                "success": True,
                "rows": [["active", 120], ["resigned", 30]],
            }
        ]
    }
    profile = build_column_profile(
        table="hr_employee",
        column="employment_status",
        schema="company",
        stats_exec=stats,
        values_exec=values,
        enum_max_distinct=64,
    )
    assert profile["enum_like"] is True
    assert profile["row_count"] == 150
    assert profile["distinct_count"] == 2
    assert profile["null_count"] == 5
    assert profile["value_counts"] == [
        {"value": "active", "count": 120},
        {"value": "resigned", "count": 30},
    ]


def test_build_column_profile_high_cardinality():
    stats = {"statements": [{"success": True, "rows": [[10000, 9800, 0]]}]}
    values = {"statements": [{"success": True, "rows": [["id-1", 1], ["id-2", 1]]}]}
    profile = build_column_profile(
        table="hr_employee",
        column="emp_no",
        schema="company",
        stats_exec=stats,
        values_exec=values,
        enum_max_distinct=64,
    )
    assert profile["enum_like"] is False
    assert len(profile["value_counts"]) == 2
