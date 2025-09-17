From ba06450c809efa5ec5ded65e5b682ccd7f82b989 Mon Sep 17 00:00:00 2001
From: blobfish <blobfish@gmx.com>
Date: Mon, 4 Jul 2022 11:40:51 -0400
Subject: [PATCH 12/18] Allow blending of faces less than 5 degrees. See
 following:

    bfb# 000006

    ChFi3d_Builder: PerformElement: Use G1 toleranced overload of IsTangentFaces
    ChFi3d: Adding IsTangentFaces overload with G1 tolerance parameter

    results of this change through occt public regression tests:
        testgrid blend
            No regressions
            Total cases: 13 BAD, 433 OK, 29 SKIPPED
---
 src/ChFi3d/ChFi3d.cxx           | 10 +++++++++-
 src/ChFi3d/ChFi3d.hxx           |  6 ++++++
 src/ChFi3d/ChFi3d_Builder_1.cxx |  2 +-
 3 files changed, 16 insertions(+), 2 deletions(-)

diff --git a/src/ChFi3d/ChFi3d.cxx b/src/ChFi3d/ChFi3d.cxx
index 702b83b1de..784ee06bf2 100644
--- a/src/ChFi3d/ChFi3d.cxx
+++ b/src/ChFi3d/ChFi3d.cxx
@@ -130,6 +130,13 @@ ChFiDS_TypeOfConcavity ChFi3d::DefineConnectType(const TopoDS_Edge&     E,
   }
 }
 
+Standard_Boolean ChFi3d::IsTangentFaces(const TopoDS_Edge&  theEdge,
+                                        const TopoDS_Face&  theFace1,
+                                        const TopoDS_Face&  theFace2,
+                                        const GeomAbs_Shape theOrder)
+{
+  return ChFi3d::IsTangentFaces(theEdge, theFace1, theFace2, 0.1, theOrder);
+}
 //=======================================================================
 //function : IsTangentFaces
 //purpose  : 
@@ -137,6 +144,7 @@ ChFiDS_TypeOfConcavity ChFi3d::DefineConnectType(const TopoDS_Edge&     E,
 Standard_Boolean ChFi3d::IsTangentFaces(const TopoDS_Edge&  theEdge,
                                         const TopoDS_Face&  theFace1,
                                         const TopoDS_Face&  theFace2,
+                                        Standard_Real G1Tol,
                                         const GeomAbs_Shape theOrder)
 {
   if (theOrder == GeomAbs_G1 && BRep_Tool::Continuity(theEdge, theFace1, theFace2) != GeomAbs_C0)
@@ -218,7 +226,7 @@ Standard_Boolean ChFi3d::IsTangentFaces(const TopoDS_Edge&  theEdge,
 
     LocalAnalysis_SurfaceContinuity aCont(aC2d1, aC2d2, aPar,
       aSurf1, aSurf2, theOrder,
-      0.001, TolC0, 0.1, 0.1, 0.1);
+      0.001, TolC0, 0.1, 0.1, G1Tol);
     if (!aCont.IsDone())
     {
       if (theOrder == GeomAbs_C2 &&
diff --git a/src/ChFi3d/ChFi3d.hxx b/src/ChFi3d/ChFi3d.hxx
index 6292eb31af..11abbe1eba 100644
--- a/src/ChFi3d/ChFi3d.hxx
+++ b/src/ChFi3d/ChFi3d.hxx
@@ -49,6 +49,12 @@ public:
                                                           const TopoDS_Face& theFace1,
                                                           const TopoDS_Face& theFace2,
                                                           const GeomAbs_Shape Order = GeomAbs_G1);
+  
+  Standard_EXPORT static Standard_Boolean IsTangentFaces (const TopoDS_Edge& theEdge,
+                                                          const TopoDS_Face& theFace1,
+                                                          const TopoDS_Face& theFace2,
+                                                          Standard_Real G1Tol,
+                                                          const GeomAbs_Shape Order = GeomAbs_G1);
 
   //! Returns  Reversed  in  Or1  and(or)  Or2  if
   //! the  concave edge  defined by the  interior of faces F1 and F2,
diff --git a/src/ChFi3d/ChFi3d_Builder_1.cxx b/src/ChFi3d/ChFi3d_Builder_1.cxx
index 7da5da1359..712b2f0210 100644
--- a/src/ChFi3d/ChFi3d_Builder_1.cxx
+++ b/src/ChFi3d/ChFi3d_Builder_1.cxx
@@ -837,7 +837,7 @@ Standard_Boolean ChFi3d_Builder::PerformElement(const Handle(ChFiDS_Spine)& Spin
   if(ff1.IsNull() || ff2.IsNull()) return 0;
 //  Modified by Sergey KHROMOV - Fri Dec 21 17:46:22 2001 End
 //if(BRep_Tool::Continuity(Ec,ff1,ff2) != GeomAbs_C0) return 0;
-  if (ChFi3d::IsTangentFaces(Ec,ff1,ff2)) return 0;
+  if (ChFi3d::IsTangentFaces(Ec,ff1,ff2, 0.001)) return 0;
 //  Modified by Sergey KHROMOV - Fri Dec 21 17:46:24 2001 Begin
 
   TopoDS_Face FirstFace = ff1;
-- 
2.45.0

