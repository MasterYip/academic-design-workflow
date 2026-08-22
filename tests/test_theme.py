from pathlib import Path

from academic_design_workflow.compiler import compile_theme, css_variables, matplotlib_rc
from academic_design_workflow.theme import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_default_theme_is_complete_and_compilable():
    theme = load_theme(ROOT / "themes" / "academic-clean.yaml")
    assert theme.meta.name == "academic-clean"
    assert {"module", "focal_module", "token"} <= set(theme.shape.vocabulary)
    assert "--adw-color-roles-data-primary-value: #315B7D;" in css_variables(theme)
    assert matplotlib_rc(theme)["svg.fonttype"] == "none"


def test_reference_theme_inherits_and_overrides_total_style():
    theme = load_theme(ROOT / "themes" / "rolling-diffusion.yaml")
    assert theme.meta.name == "rolling-diffusion"
    assert theme.shape.vocabulary["encoder"].geometry == "trapezoid"
    assert theme.color_value("data_primary") == "#3E6378"
    palette = [token.value for token in theme.color.roles.values()]
    palette += theme.color.categorical + theme.color.sequential + theme.color.diverging
    assert "#7D2EC5" not in palette


def test_intact_theme_resolves_light_paper_and_dark_brand_variants():
    theme = load_theme(ROOT / "themes" / "intact.yaml")
    assert theme.for_variant("paper").color_value("canvas") == "#F7FAFC"
    assert theme.for_variant("web").color_value("canvas") == "#050914"
    assert theme.for_variant("video").color_value("text_primary") == "#F4F7FB"


def test_compiler_emits_variant_specific_tokens(tmp_path):
    theme = load_theme(ROOT / "themes" / "intact.yaml")
    paths = {path.name for path in compile_theme(theme, tmp_path)}
    assert {"theme.paper.css", "theme.web.css", "theme.video.css"} <= paths
    assert "#050914" in (tmp_path / "theme.web.css").read_text(encoding="utf-8")
