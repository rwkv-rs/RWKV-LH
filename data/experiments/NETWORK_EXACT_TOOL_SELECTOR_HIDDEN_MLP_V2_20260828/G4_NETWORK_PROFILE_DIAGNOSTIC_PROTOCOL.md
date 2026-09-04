# G4 network-profile diagnostic protocol

This is a diagnostic, not a release gate.  The live-network V1 two-case set is
already open after the G5 Stage-A run and must not be described as an unseen
holdout.

The fixed question is whether the previously rejected **global** G4 state is a
better parent for an isolated network profile than G5.  Use G4 step 2000
(`c4e9e8ae01e829aa1c369945fa46ae287d900b3fa98dd06ae54ab2ef5d6ef946`),
because it has the highest frozen G4-dev exact score (447/480) and true-workflow
score (208/240) in the completed G4 checkpoint sweep.  Use S60 V7, physical
GPU0, temperature 0.1, top-p 1, top-k 0, one raw generation per request, and
the unchanged V1 live2 cases.

Run both cases once even if the first fails.  Record exact actions, protocol
rejections, output identity, tail checks, and service identity.  A 2/2 result
only authorizes construction of a new unseen live-network holdout; it cannot
authorize release.  Any failure determines the G6 training-data families.
