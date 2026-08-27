import struct
import uuid
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
        <Row N="SourceText"><Cell N="Value" V="$x_0$"/></Row>
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


def minimal_cfb(root_clsid: str) -> bytes:
    header = bytearray(512)
    header[:8] = bytes.fromhex("D0CF11E0A1B11AE1")
    struct.pack_into("<H", header, 30, 9)
    struct.pack_into("<I", header, 44, 1)
    struct.pack_into("<I", header, 48, 1)
    struct.pack_into("<109I", header, 76, 0, *([0xFFFFFFFF] * 108))
    fat = bytearray(b"\xff" * 512)
    struct.pack_into("<I", fat, 0, 0xFFFFFFFD)
    struct.pack_into("<I", fat, 4, 0xFFFFFFFE)
    directory = bytearray(512)
    name = "Root Entry\0".encode("utf-16le")
    directory[: len(name)] = name
    struct.pack_into("<H", directory, 64, len(name))
    directory[66] = 5
    directory[80:96] = uuid.UUID(root_clsid).bytes_le
    return bytes(header + fat + directory)


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
    assert audit["shapes"][0]["shape_data"]["SourceText"] == "$x_0$"
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


def test_office_math_exception_is_exact_and_narrow(tmp_path):
    path = tmp_path / "office-math.vsdx"
    page = """<?xml version="1.0" encoding="UTF-8"?>
    <PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
      <Shapes><Shape ID="1" NameU="equation" Type="Foreign">
        <Section N="Property">
          <Row N="SemanticID"><Cell N="Value" V="equation"/></Row>
          <Row N="Role"><Cell N="Value" V="office_math"/></Row>
          <Row N="SourceText"><Cell N="Value" V="$x/y$"/></Row>
          <Row N="OfficeMathProgID"><Cell N="Value" V="Word.Document.12"/></Row>
          <Row N="OfficeMathEditable"><Cell N="Value" V="true"/></Row>
        </Section><ForeignData/></Shape></Shapes>
    </PageContents>"""
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("visio/pages/page1.xml", page)
        package.writestr("visio/media/image1.emf", b"preview")
    strict = audit_vsdx(path)
    assert strict["native_semantic_pass"] is False
    allowed = audit_vsdx(path, allowed_office_math_semantic_ids=("equation",))
    assert allowed["office_math_exception_applied"] is True
    assert allowed["native_semantic_pass"] is True
    wrong = audit_vsdx(path, allowed_office_math_semantic_ids=("other",))
    assert wrong["native_semantic_pass"] is False


def test_axmath_exception_requires_exact_metadata_and_embedding_clsid(tmp_path):
    path = tmp_path / "axmath.vsdx"
    page = """<?xml version="1.0" encoding="UTF-8"?>
    <PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
      <Shapes><Shape ID="1" NameU="axmath_equation" Type="Foreign">
        <Section N="Property">
          <Row N="SemanticID"><Cell N="Value" V="axmath_equation"/></Row>
          <Row N="Role"><Cell N="Value" V="equation"/></Row>
          <Row N="SourceText"><Cell N="Value" V="$x/y$"/></Row>
          <Row N="DisplayLatex"><Cell N="Value" V="$\\frac{x}{y}$"/></Row>
          <Row N="AxMathProgID"><Cell N="Value" V="Equation.AxMath"/></Row>
          <Row N="AxMathCLSID"><Cell N="Value" V="{B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28}"/></Row>
        </Section><ForeignData/></Shape></Shapes>
    </PageContents>"""
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("visio/pages/page1.xml", page)
        package.writestr("visio/media/image1.emf", b"preview")
        package.writestr(
            "visio/embeddings/oleObject1.bin",
            minimal_cfb("b18c2bcc-4e79-436a-a2a5-a7f8d25a9a28"),
        )
    strict = audit_vsdx(path)
    assert strict["native_semantic_pass"] is False
    allowed = audit_vsdx(path, allowed_axmath_semantic_ids=("axmath_equation",))
    assert allowed["axmath_exception_applied"] is True
    assert allowed["embedding_root_clsids"] == {
        "visio/embeddings/oleObject1.bin": "b18c2bcc-4e79-436a-a2a5-a7f8d25a9a28"
    }
    assert allowed["native_semantic_pass"] is True
    wrong = audit_vsdx(path, allowed_axmath_semantic_ids=("other",))
    assert wrong["native_semantic_pass"] is False
