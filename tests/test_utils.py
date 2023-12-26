from material_parsers.commons.utils import rewrite_comparison_symbol


def test_rewrite_comparison_symbol_should_not_rewrite():
    assert rewrite_comparison_symbol(">10") == ">10"


def test_rewrite_comparison_symbol_should_rewrite():
    assert rewrite_comparison_symbol("0 <") == "> 0"


def test_rewrite_comparison_symbol_should_rewrite2():
    assert rewrite_comparison_symbol("123231212110 <") == "> 123231212110"
