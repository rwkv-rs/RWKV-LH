# RWKV-LH Stage 1 selector state tuning

This is a 500-row selector-only continuation corpus derived from the frozen Round1 residual. It teaches outer protocol identity (`select_tool`), not generic task execution. The 79-row dev split is frozen and disjoint. Training requires RWKV-PEFT `loss_mask=target_suffix`.
