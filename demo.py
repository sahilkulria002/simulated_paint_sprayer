from pxr import Usd, UsdGeom
import os
p = os.path.abspath("outputs/frame_0000.usda")
stage = Usd.Stage.Open(p)

for prim in ["/World/ArmBasePos",
             "/World/ArmBasePos/ShoulderJoint",
             "/World/ArmBasePos/ShoulderJoint/ElbowPos",
             "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos",
             "/Wall"]:
    xf = UsdGeom.Xformable(stage.GetPrimAtPath(prim))
    print(prim, xf.ComputeLocalToWorldTransform(0).ExtractTranslation())
