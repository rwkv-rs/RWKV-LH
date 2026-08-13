# Round9 离线与确定性门禁

- 运行前产品测试：`184 passed in 10.63s`
- 首次 Control：`29/30`；LH-M04 夹具仍输出 Round8 旧 binding array。
- 夹具只迁移输出协议后 Control：`30/30`，产品测试 `184/184`。
- 运行后产品测试：`184 passed in 10.63s`；Control：`30/30`。

失败预检与迁移后结果均保留在 `Round9_pre_run/`，没有删除失败记录或更改验收口径。

- protocol SHA-256：`6c750c335b3fdec73e100a35272178e06748ff86732f44bca94f5ee4d1ab3be6`
- results SHA-256：`548040b44914975103c6b5d9c530490f41d20f29bf04a330c1a0a4582fbe5712`
- G1i analysis SHA-256：`594e99a4e544c294ddfb6a4fa7351f3d74b7c55bb60b9e02e122785ebb6a42e7`
- failed/fixed/post Control SHA-256：`ba636b9fecc7ebfe6a67a6e5616062500a133da98b4dc58a3d3b99100f75da5f` /
  `4fec636625bf716aab38efa90e87cbdea1ac54cc9b4404df5d90b276a115214b` /
  `6f6cb1a3b222157390eeb8cc0af2d1c1e5b1d05dd4078ee40644349e5f401a1f`
