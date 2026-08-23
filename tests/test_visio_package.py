import zipfile

from academic_design_workflow.visio.package import audit_vsdx, diff_audits

PAGE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
  <PageSheet>
    <Section N="Property"><Row N="SceneHash"><Cell N="Value" V="abc123"/></Row></Section>
  </PageSheet>
  <Shapes>
    <Shape ID="1" NameU="block_a" Type="Shape">
      <Cell N="PinX" V="{pin_x}"/><Cell N="PinY" V="1"/>
      <Cell N="Width" V="2"/><Cell N="Height" V="1"/>
      <Section N="Property">
        <Row N="SemanticID"><Cell N="Value" V="block_a"/></Row>
        <Row N="Role"><Cell N="Value" V="graph_node"/></Row>
      </Section>
      <Text>Block A</Text>
    </Shape>
    <Shape ID="2" NameU="block_b" Type="Shape">
      <Cell N="PinX" V="4"/><Cell N="PinY" V="1"/>
      <Section N="Property">
        <Row N="SemanticID"><Cell N="Value" V="block_b"/></Row>
      </Section>
    </Shape>
    <Shape ID="3" NameU="edge_ab" Type="Shape">
      <Cell N="OneD" V="1"/>
      <Section N="Property">
        <Row N="SemanticID"><Cell N="Value" V="edge_ab"/></Row>
        <Row N="Source"><Cell N="Value" V="block_a"/></Row>
        <Row N="Target"><Cell N="Value" V="block_b"/></Row>
      </Section>
    </Shape>
  </Shapes>
  <Connects>
    <Connect FromSheet="3" FromCell="BeginX" ToSheet="1" ToCell="Connections.east.X"/>
    <Connect FromSheet="3" FromCell="EndX" ToSheet="2" ToCell="Connections.west.X"/>
  </Connects>
</PageContents>
"""


def write_vsdx(path, pin_x="1"):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("visio/pages/page1.xml", PAGE_TEMPLATE.format(pin_x=pin_x))


def test_offline_package_audit_proves_native_semantic_content(tmp_path):
    path = tmp_path / "native.vsdx"
    write_vsdx(path)
    audit = audit_vsdx(path)
    assert audit["shape_records"] == 3
    assert audit["native_shape_records"] == 3
    assert audit["semantic_shape_records"] == 3
    assert audit["connector_records"] == 1
    assert audit["connect_records"] == 2
    assert audit["group_records"] == 0
    assert audit["foreign_data_records"] == 0
    assert audit["media_parts"] == []
    assert audit["duplicate_semantic_ids"] == []
    assert audit["page_shape_data"]["SceneHash"] == "abc123"
    assert audit["native_semantic_pass"] is True
    assert audit["native_semantic_violations"] == []


def test_semantic_package_diff_reports_only_changed_geometry(tmp_path):
    before_path = tmp_path / "before.vsdx"
    after_path = tmp_path / "after.vsdx"
    write_vsdx(before_path, pin_x="1")
    write_vsdx(after_path, pin_x="1.5")
    result = diff_audits(audit_vsdx(before_path), audit_vsdx(after_path))
    assert result["added_semantic_ids"] == []
    assert result["removed_semantic_ids"] == []
    assert [change["semantic_id"] for change in result["changed"]] == ["block_a"]
    assert result["connects_added"] == []
    assert result["connects_removed"] == []
