Here is the transformation of the provided source document from PDF to markdown format:

# Thanos compactor halted
##### SOLUTION VERIFIED - Updated December 6 2024 at 6:48 PM

### Environment
Red Hat Advanced Cluster Management Observability 2.X

### Issue
The **Thanos Compactor** is an essential component for the stability of the Observability functionality in Advanced Cluster Management (ACM). The Compactor's job is to:
*   Delete blocks in object storage when they fall outside the configured metrics retention period.
*   Down-sampling blocks to improve query latency

A non-working or halted compactor could have the following negative impacts on the Observability functionality:
*   Object storage disk space usage always increasing.
*   Increased metric query latency, including dashboards slowly loading in Grafana.
*   Increased disk space usage on the Compactor and Store Gateway PVCs.
*   Alert **ACMThanosCompactHalted** firing on the Hub (ACM 2.9+).

### Resolution
Determine why the compactor has halted. See more in the "Diagnostic Steps" section. Then follow the steps below as appropriate.

**Solution 1: Halted due to "no space left on device"**
*   Increase the storage space of the Compactor PVC **data-observability-thanos-compact-0** in namespace **open-cluster-management-observability** to ensure it has sufficient space.
*   It is also a good idea to double check that the **data-observability-thanos-store-shard-** PVCs have sufficient space as well.
*   Restart the Thanos Compact pod. This can be done by scaling the pods in the statefulset **observability-thanos-compact** down to 0. It will automatically be scaled back up to 1.
When the compactor is healthy again and the **acm_thanos_compact_todo_compactions** metric is low, it might be possible to decrease the PVC sizes again.

**Solution 2: Halted due to "corrupted blocks"**
In the compactor logs:
*   In this case block "**01HKZYEZ2DVDQXF1STVEXAMPLE**" is corrupted.
*   Attempt to repair the block:
    *   If the repair failed, we need to fully delete the block. Unfortunately, this means the data within this block is lost. First we mark the block for deletion, and then we process the deletion of the marked blocks.
*   Restart the Thanos Compact pod. This can be done by scaling the pods in the statefulset **observability-thanos-compact** down to 0 then back to 1.

```
$ oc logs observability-thanos-compact-0 [..] ts=2024-01-24T15:34:51.948653839Z caller=compact.go:491 level=error msg="critical error detected; halting" err="compaction: group 0@15699422364132557315: compact blocks [/var/thanos/compact/compact/0@15699422364132557315/01HKZGQGJCKQWF3XMA8EXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HKZQK7TD06J2XWGR5EXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HKZYEZ2DVDQXF1STVEXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HM05APAHXBQSNC0N5EXAMPLE]: populate block: chunk iter: cannot populate chunk 8 from block 01HKZYEZ2DVDQXF1STVEXAMPLE: segment index 0 out of range" [..]
```
```bash
$ oc rsh observability-thanos-compact-0 [..] thanos tools bucket verify -r --objstore.config="$OBJSTORE_CONFIG" --id=01HKZYEZ2DVDQXF1STVEXAMPLE
thanos tools bucket mark --id "01HKZYEZ2DVDQXF1STVEXAMPLE" --objstore.config="$OBJSTORE_CONFIG" --marker=deletion-mark.json --details=DELETE # Marks the broken block for deletion.
thanos tools bucket cleanup --objstore.config="$OBJSTORE_CONFIG" # Does the cleanup of the marked blocks.
oc scale statefulset observability-thanos-compact -n open-cluster-management-observability --replicas=0
oc scale statefulset observability-thanos-compact -n open-cluster-management-observability --replicas=1
```

**Note**: Multiple blocks may be corrupted. Keep monitoring the compactor health (see below) and keep repairing or deleting problematic blocks.

**Solution 3: any kind of "access key error"**
*   Confirm and validate that the access key in the **thanos-object-storage** secret is correct.
*   Confirm the permissions for your storage are correctly set - refer to the documentation.
*   Restart the **thanos-compactor** with the same method as above.

**Note**: If the configuration is correct it may be that previous changes have not been taken into account yet - if so restarting the pod will fix that.

### Monitoring the compactor health
After the compactor has started up again, it is important to keep a track on the health of the compactor.
*   On ACM 2.9+ ensure that the **ACMThanosCompactHalted** alert on the hub is not firing.
*   On all versions of ACM it is possible to check if the compactor is halted by checking the metric **acm_thanos_compact_halted**. It should be **0** when the compactor is not halted. This can be checked in the OCP console in the Observability->Metrics tab.
*   If the compactor has not been working for a while the **acm_thanos_compact_todo_compactions** metric is expected to be high. After restarting the compactor, keep an eye on this metric to ensure that the number of todo compactions is decreasing. It might take several weeks to work through the full compaction backlog and for the todo compactions to fall down to below 10.

Ensure the compactor is always running, if it halts again, please review the resolution steps once more.

### Root Cause
*   Compactor halted due to PVCs running out of space
*   Compactor halted due to corrupted blocks

### Diagnostic Steps
#### Determining if the compactor is halted
*   Alert **ACMThanosCompactHalted** is firing on the Hub (ACM 2.9+)
*   Metric **acm_thanos_compact_halted** = 0.
*   Metric **acm_thanos_compact_todo_compactions** is high and increasing.

#### Determining the reason for the halted compactor
To determine why the compactor has halted, we need to investigate the compactor logs. This can be done with:

```bash
oc scale statefulset observability-thanos-compact -n open-cluster-management-observability --replicas=0
oc scale statefulset observability-thanos-compact -n open-cluster-management-observability --replicas=1
$ oc logs observability-thanos-compact-0
```

*   If the log line looks as below, the problem is due to the compactor PVC running out of space:
    ```
    $ oc logs observability-thanos-compact-0 | grep "halting"
    ts=2024-01-24T15:34:51.948653839Z caller=compact.go:491 level=error msg="critical error detected; halting" err="compaction: group 0@5827190780573537664: compact blocks [ /var/thanos/compact/compact/0@15699422364132557315/01HKZGQGJCKQWF3XMA8EXAMPLE]: 2 errors: populate block: add series: write series data: write /var/thanos/compact/compact/0@15699422364132557315/01HKZGQGJCKQWF3XMA8EXAMPLE.tmp-for-creation/index: no space left on device; write /var/thanos/compact/compact/0@15699422364132557315/01HKZGQGJCKQWF3XMA8EXAMPLE.tmp-for-creation/index: no space left on device"
    ```

*   If the log line looks similar to below the compactor halted due to corrupted blocks:
    ```
    ts=2024-01-24T15:34:51.948653839Z caller=compact.go:491 level=error msg="critical error detected; halting" err="compaction: group 0@15699422364132557315: compact blocks [/var/thanos/compact/compact/0@15699422364132557315/01HKZGQGJCKQWF3XMA8EXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HKZQK7TD06J2XWGR5EXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HKZYEZ2DVDQXF1STVEXAMPLE /var/thanos/compact/compact/0@15699422364132557315/01HM05APAHXBQSNC0N5EXAMPLE]: populate block: chunk iter: cannot populate chunk 8 from block 01HKZYEZ2DVDQXF1STVEXAMPLE: segment index 0 out of range"
    ```

*   In the case of an access key issue, the following may show (there could be variants):
    ```
    ts=2024-10-29T19:32:23.096730797Z caller=compact.go:538 level=error msg="retriable error" err="compaction: sync: BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:32:23.139590286Z caller=runutil.go:100 level=error msg="function failed. Retrying in next tick" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:32:23.139659186Z caller=compact.go:604 level=error msg="retriable error" err="syncing metas: BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:32:23.182504977Z caller=compact.go:633 level=error msg="retriable error" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:33:23.103484806Z caller=runutil.go:100 level=error msg="function failed. Retrying in next tick" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:34:23.103483855Z caller=runutil.go:100 level=error msg="function failed. Retrying in next tick" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:35:23.102664755Z caller=runutil.go:100 level=error msg="function failed. Retrying in next tick" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ts=2024-10-29T19:36:23.100232906Z caller=runutil.go:100 level=error msg="function failed. Retrying in next tick" err="BaseFetcher: iter bucket: The access key ID you provided does not exist in our records."
    ```