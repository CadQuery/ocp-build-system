// M1425 independent OCCT8 probe: no Python binding or frontend is involved.
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRep_Tool.hxx>
#include <TopoDS_Iterator.hxx>
#include <Standard_Version.hxx>
#include <iomanip>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopAbs_ShapeEnum.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <Law_Linear.hxx>
#include <Standard_Failure.hxx>
#include <gp_Pnt.hxx>
#include <iostream>
#include <cmath>

int main() {
  const auto shape = BRepPrimAPI_MakeBox(gp_Pnt(-20, -10, -5), 40, 20, 10).Shape();
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(shape, TopAbs_EDGE, edges);
  for (int i = 1; i <= edges.Extent(); ++i) {
    const auto edge = TopoDS::Edge(edges.FindKey(i));
    GProp_GProps props;
    BRepGProp::LinearProperties(edge, props);
    if (std::abs(props.Mass() - 40) > 1e-8 ||
        props.CentreOfMass().Distance(gp_Pnt(0, 10, 5)) > 1e-8) continue;
    try {
      BRepFilletAPI_MakeFillet builder(shape);
      builder.Add(edge);
      const int contour = builder.Contour(edge);
      Handle(Law_Linear) law(new Law_Linear);
      law->Set(0, 1, builder.Length(contour), 3);
      builder.SetRadius(law, contour, 1);
      builder.Build();
      if (!builder.IsDone()) {
        std::cout << "{\"is_done\":false}\n";
        return 1;
      }
      const auto result = builder.Shape();
      GProp_GProps volume;
      BRepGProp::VolumeProperties(result, volume);
      // Corner area removed is (1 - pi/4) r^2. Integrate the linear 1->3 law
      // over 40 mm: integral(r^2) = L (r0^2 + r0*r1 + r1^2) / 3.
      const double expected = 8000.0 - (1.0 - std::acos(-1.0) / 4.0) * 40.0 * (1.0 + 3.0 + 9.0) / 3.0;
      TopTools_IndexedMapOfShape solids;
      TopExp::MapShapes(result, TopAbs_SOLID, solids);
      bool wrapper_ok = result.ShapeType() == TopAbs_SOLID;
      if (result.ShapeType() == TopAbs_COMPOUND) {
        TopoDS_Iterator children(result);
        if (children.More() && children.Value().ShapeType() == TopAbs_SOLID) {
          children.Next();
          wrapper_ok = !children.More();
        }
      }
      bool closed = false;
      if (solids.Extent() == 1) {
        TopTools_IndexedMapOfShape shells;
        TopExp::MapShapes(solids.FindKey(1), TopAbs_SHELL, shells);
        closed = shells.Extent() > 0;
        for (int shell = 1; shell <= shells.Extent(); ++shell)
          closed = closed && BRep_Tool::IsClosed(shells.FindKey(shell));
      }
      const bool valid = wrapper_ok && solids.Extent() == 1 && closed && BRepCheck_Analyzer(result).IsValid();
      const bool closed_form = std::abs(volume.Mass() - expected) < 0.01;
      std::cout << std::setprecision(17) << "{\"is_done\":true,\"valid\":" << (valid ? "true" : "false")
                << ",\"volume_mm3\":" << volume.Mass() << ",\"expected_mm3\":" << expected
                << ",\"shape_type\":" << static_cast<int>(result.ShapeType())
                << ",\"solid_count\":" << solids.Extent()
                << ",\"closed\":" << (closed ? "true" : "false")
                << ",\"brep_valid\":" << (BRepCheck_Analyzer(result).IsValid() ? "true" : "false")
                << ",\"closed_form_ok\":" << (closed_form ? "true" : "false") << "}\n";
      return valid && closed_form ? 0 : 3;
    } catch (const Standard_Failure& failure) {
      std::cout << "{\"is_done\":false,\"exception\":\"" << failure.GetMessageString() << "\"}\n";
      return 1;
    }
  }
  std::cout << "{\"error\":\"authored physical edge missing\"}\n";
  return 2;
}
