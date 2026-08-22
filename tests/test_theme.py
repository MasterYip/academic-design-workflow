from pathlib import Path

from academic_design_workflow.compiler import css_variables, matplotlib_rc
from academic_design_workflow.theme import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_default_theme_is_complete_and_compilable():
    theme = load_theme(ROOT / "themes" / "academic-clean.yaml")
    assert theme.meta.name == "academic-clean"
    assert {"module", "focal_module", "token"} <= set(theme.shape.vocabulary)
    assert "--adw-color-roles-data-primary-value: #315B7D;" in css_variables(theme)
    assert matplotlib_rc(theme)["svg.fonttype"] == "none"

