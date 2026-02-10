# MCOA for Metrics Documentation

Table of Contents

[Introduction](#introduction)

[Architecture](#architecture)

[Logical Diagram](#logical-diagram)

[Differences Summary with Previous Version](#differences-summary-with-previous-version)

[Enabling MCOA for Metrics](#enabling-mcoa-for-metrics)

[Configuration APIs](#configuration-apis)

[The PrometheusAgents](#the-prometheusagents)

[The ScrapeConfigs](#the-scrapeconfigs)

[The PrometheusRules](#the-prometheusrules)

[Migrate Custom Allowlist](#migrate-custom-allowlist)

[The AddonDeploymentConfig](#the-addondeploymentconfig)

[Common configurations](#common-configurations)

[Sampling rate](#sampling-rate)

[Adding Custom Metrics](#adding-custom-metrics)

[User Workloads and ScrapeConfig Namespaces](#user-workloads-and-scrapeconfig-namespaces)

[Federating User Workloads from CMO](#federating-user-workloads-from-cmo)

[Federating User Workloads from COO](#federating-user-workloads-from-coo)

[Adapting the Default Metrics](#adapting-the-default-metrics)

[Exporting Metrics to External Endpoints](#exporting-metrics-to-external-endpoints)

[Monitoring the Addon](#monitoring-the-addon)

[COO Compatibility](#coo-compatibility)

[Non OCP Platforms Support](#non-ocp-platforms-support)

[Alert forwarding in MCOA](#alert-forwarding-in-mcoa)

[Grafana](#grafana)

[FAQ](#faq)

[Migrating your Custom Allow-List ConfigMaps](#migrating-your-custom-allow-list-configmaps)

[Resiliency to Network Partitions with the Hub](#resiliency-to-network-partitions-with-the-hub)

[Can a Managed Cluster Belong to Multiple Placements?](#can-a-managed-cluster-belong-to-multiple-placements?)

[Disabling Metrics Collection on a Specific Cluster](#disabling-metrics-collection-on-a-specific-cluster)

[Troubleshooting Custom Metrics Collection](#troubleshooting-custom-metrics-collection)

[Deploying the AddOn Configuration Changes Progressively](#deploying-the-addon-configuration-changes-progressively)

[Avoiding Reconciliation of Unavailable Clusters](#avoiding-reconciliation-of-unavailable-clusters)

[Creating a Placement for Single Node Openshift Spokes](#creating-a-placement-for-single-node-openshift-spokes)

[Annexes](#annexes)

[The Placement API – Basics](#the-placement-api-–-basics)

# Introduction {#introduction}

The MultiCluster Observability Addon (MCOA) is the new version of the MultiCluster Observability Operator. This release focuses on the new metrics collectors. MCOA favors the use of standard open-source components for metrics collection.

The MCOA metrics collection offers several key advantages:

* **Improved Configurability:** Users gain access to a wider range of configurations by directly configuring custom resources on spokes. MCOA ensures consistency by enforcing invariants through server-side apply.  
* **Increased Metrics Federation Scalability:** The use of distinct `scrapeConfigs`, each independently federated from the in-cluster Prometheus, enhances the collector's scalability as federated cardinality grows.  
* **More Performant Remote Write with Network Partition Resiliency:** The standard remoteWrite implementation efficiently sends metrics from spokes to the hub with better payload management and performance. It also provides resiliency to network partitions between spokes and the hub for up to one hour.

# Architecture {#architecture}

## Logical Diagram {#logical-diagram}

![][image1]

## Differences Summary with Previous Version {#differences-summary-with-previous-version}

### New Metrics Collector Workloads

Workloads on managed clusters now use established upstream projects. The Endpoint operator and Metrics Collector are replaced by the COO's Prometheus Operator and a Prometheus Agent. Their function—federating, downsampling, and remote writing metrics to the hub—remains the same.

### Leveraging Standard Upstream APIs for Configuration

Metrics collection is now configured using upstream standard Kubernetes APIs (CRs), replacing the previous single MCO CR with PrometheusAgent, ScrapeConfig, and PrometheusRule APIs. These APIs configure deployed workloads, including how and where metrics are federated and sent. For each CR, the operator ensures critical fields are set via server-side apply, while users can configure the remaining fields as needed.

### Fine-Grained Configuration with OCM APIs

Configuration deployments are now fully integrated with Open Cluster Management APIs, enabling fine-grained selection of managed cluster sets and their associated configurations. This relies on the Placement API for grouping clusters, and the AddOnDeploymentConfig can be used to support the desired options.

# Enabling MCOA for Metrics {#enabling-mcoa-for-metrics}

To enable either platform monitoring (required) and optionally user workload monitoring, add the following sections to the `MultiClusterObservability` custom resource:

```
apiVersion: observability.open-cluster-management.io/v1beta2
kind: MultiClusterObservability
metadata:
  name: observability
spec:
  capabilities:
    platform:
      metrics:
        default:
          enabled: true # <-- required
    userWorkloads:
      metrics:
        default:
          enabled: true # <-- optional
```

This configuration change has these effects:

1. **Removes unnecessary resources**, mainly**:**  
   * `endpoint-observability-operator`  
   * `metrics-collector-deployment`  
2. **Deploys the `multicluster-observability-addon-manager`** in the `open-cluster-management-observability` namespace.  
3. **Creates MCOA-specific Grafana dashboards** and deprecates old ones.

The `multicluster-observability-addon-manager` then performs these steps:

1. **Creates default configuration resources** for MCOA**:**  
   * Default platform PrometheusAgent (and optionally user workloads) for each placement referenced in the `ClusterManagementAddon` named `multicluster-observability-addon`.  
   * Default platform ScrapeConfigs for the dashboards.  
2. **Adds the default configurations to the `ClusterManagementAddon`** named `multicluster-observability-addon` in each referenced placement.

These default configurations are then deployed on each spoke contained in the placements in the `open-cluster-management-agent-addon` (by default) namespace.

# Configuration APIs {#configuration-apis}

MCOA offers the following APIs (or configurations) for configuring metrics collection:

* **PrometheusAgents:** These act as the metrics collectors. You can define what prometheus server is used to federate metrics from, the default scrape interval and where the metrics must be sent.  
* **ScrapeConfigs:** These define which metrics to collect.  
* **PrometheusRules**: aggregation rules evaluated by the target cluster’s prometheus. The resulting metric can be referenced in scrapeConfigs.

Beyond those metrics specific APIs, it is configured using the standard Open Cluster Management APIs such as:

* **AddonDeploymentConfig**: usual addon options like the installation namespace, node selector etc.  
* **ClusterManagementAddon**: what configurations to deploy on which managed clusters.

Whenever a new placement is referenced in the ClusterManagementAddon, the addon manager will create a specific default PrometheusAgent and automatically add it to the placement configurations in the the ClusterManagementAddon, along with the required default ScrapeConfigs and PrometheusRules. 

When creating a custom configuration, like a new ScrapeConfig, the user must add it in the placement configurations list of the ClusterManagementAddon so that it takes effect.

On the managed clusters, the resources are deployed in the installation namespace configured by the ClusterManagementAddon. The default value is `open-cluster-management-agent-addon`.

## The PrometheusAgents {#the-prometheusagents}

For **each** **placement**, the `multicluster-observability-addon-manager` searches for `PrometheusAgent` resources that have the following labels:

```
  - app.kubernetes.io/component: <platform-metrics-collector> or <user-workload-metrics-collector>
  - app.kubernetes.io/managed-by: multicluster-observability-addon
  - placement-ref-name: <the placement ref name>
  - placement-ref-namespace: <the placement ref namespace>

```

They are automatically created by the **`multicluster-observability-addon-manager`** and added to the clusterManagementAddOn configurations for the placement. The manager creates a default configuration with sensible values that can be overridden by the user. It then enforces invariants using server-side apply, leaving other fields intact.

### The Default Configuration

The default configuration of the deployed prometheus agent sets sensible values for fields that are configurable by the user. This includes fields like the `logLevel`, `scrapeInterval` etc.  
These resources have their name prefixed with the `mcoa-default` string and contain the expected label by the addon manager:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: PrometheusAgent
metadata:
  name: mcoa-default-platform-metrics-collector-global
  labels:
    app.kubernetes.io/component: platform-metrics-collector
    app.kubernetes.io/managed-by: multicluster-observability-addon
    placement-ref-name: global
    placement-ref-namespace: open-cluster-management-global-set
spec:
  ...
```

### The Enforced Configuration

MCOA enforces some configurations that are necessary for operating correctly. This is achieved by using [server-side apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/). The enforced configuration is tracked by the managedFields field:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: PrometheusAgent
metadata:
  name: mcoa-default-user-workload-metrics-collector-global
  namespace: open-cluster-management-observability
  managedFields:
    - manager: multicluster-observability-addon
      operation: Apply
      ... <-- tracking of the managed fields
  
```

The enforced fields mainly consists of:

* The "ocp-monitoring" `scrapeClass`: This contains connection details for federating metrics from the in-cluster Prometheus. You can configure custom `MetricRelabelings` here.  
* The `scrapeConfigSelector`: This is configured to monitor the `PrometheusAgent` namespace for platform metrics and all namespaces for user workloads.  
* The "acm-observability" `remoteWrite` config: This pushes metrics to the hub. You can adapt the `queueConfig` (see [Prometheus Remote Write Tuning Documentation](https://prometheus.io/docs/practices/remote_write/)) and `remoteTimeout` as needed.  
* Some secrets and ConfigMaps.

If the user modifies an enforced field such as removing the remote write configuration to the hub, it is automatically reverted by the addon manager.

## The ScrapeConfigs  {#the-scrapeconfigs}

Each `ScrapeConfig` defines a set of metrics to be independently federated from the in-cluster Prometheus.

### Common configuration {#common-configuration}

MCOA uses the [Federation API](https://prometheus.io/docs/prometheus/latest/federation/) from the in-cluster Prometheus to downsample and extract the required metric subset. All `ScrapeConfigs` must include these fields:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: ScrapeConfig
metadata:
  name: some-metrics-to-collect
  namespace: open-cluster-management-observability
  labels:
    app.kubernetes.io/component: <platform-metrics-collector> or <user-workload-metrics-collector>
spec:
  jobName: some-job-name
  metricsPath: /federate
  params:
    match[]:
    - '{__name__="up"}' # The metric name and labels filtering
```

This configuration tells Prometheus to federate metrics using the `/federate` URL path and the provided URL parameters. In the example above, it collects the `up` metric.

### Enforced Configuration

For **platform monitoring**, the source server is specified with:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: ScrapeConfig
spec:
  # Omitting the rest of the configuration
  # ...  scrapeClass: ocp-monitoring
  scheme: HTTPS
  staticConfigs:
  - targets:
    - prometheus-k8s.openshift-monitoring.svc:9091
```

   
These fields are enforced by MCOA when the scrapeConfig contains the label `app.kubernetes.io/component` set to `platform-metrics-collector`. 

For user workload monitoring, this is configurable by the user. By default, the source server is specified with:

```
apiVersion: monitoring.coreos.com/v1alpha1
kind: ScrapeConfig
spec:
  # Omitting the rest of the configuration
  # ...
  scrapeClass: ocp-monitoring
  scheme: HTTPS
  staticConfigs:
  - targets:
    - prometheus-user-workload.openshift-user-workload-monitoring.svc:9092
```

### The default platform metrics

MCOA automatically generates a set of `ScrapeConfigs` which include the essential metrics needed for its functional dashboards. This set of metrics is highly optimized and curated for performance. These generated `ScrapeConfigs` are automatically deployed to all managed clusters ("spokes"). All placements referenced within the `ClusterManagementAddon` will automatically receive these configurations.

Some default metrics are specific to certain platforms:

* `platform-metrics-hcp` (For HyperShift HostedControlPlanes)  
* `platform-metrics-virtualization`

While other default metrics are common across all platforms:

* `platform-metrics-alerts`  
* `platform-metrics-default`

All listed `ScrapeConfigs` are deployed to all managed clusters. When the target managed cluster doesn’t hold the listed metrics, it has no effect.

## The PrometheusRules {#the-prometheusrules}

A monitoring system performance depends on the number of metrics it collects across all managed clusters. To limit the cardinality of the collected metrics you should preaggregate them in their observed form at the hub level. This can be done through the prometheusRules API. As for the prometheusAgent and scrapeConfig, you must add the expected label values for [`app.kubernetes.io/component`](http://app.kubernetes.io/component):

* `platform-metrics-collector`: For platform metrics.  
* `user-workload-metrics-collector`: For user workload metrics.

These rules can also define alerts evaluated on the managed clusters.

For Prometheus rules targeting user-workloads, you must include the specific annotation `observability.open-cluster-management.io/target-namespace` to designate the namespace where the rule should be deployed.

Failure to include this annotation will result in the rules being deployed to the default installation namespace. This default namespace contains the `openshift.io/cluster-monitoring=true` label, which means the rules will not be monitored by the in-cluster user-workload monitoring stack.

| ⚠️Make sure you use the PrometheusRule resource from the [monitoring.coreos.com](http://monitoring.coreos.com) group. While we use monitoring.rhobs for the ScrapeConfig and PrometheusAgent. |
| :---- |

| ⚠️PrometheusRule configurations for user workloads are only supported when federating from CMO. COO will be supported in future releases. |
| :---- |

## Migrate Custom Allowlist {#migrate-custom-allowlist}

For MCO, you could add custom metrics through a configmap that is named “observability-metrics-custom-allowlist” and applied in the “open-cluster-management-observability” namespace. Custom metrics, renames, and recording rules could be defined using this resource. An example of this configmap used for custom metrics, called an allowlist, is the following:

```
kind: ConfigMap
apiVersion: v1
metadata:
  name: observability-metrics-custom-allowlist
data:
  metrics_list.yaml: |
    names:
      - up
    matches:
      - __name__="container_memory_cache",container!=""
    recording_rules:
      - record: container_memory_rss:sum
        expr: sum(container_memory_rss) by (container, namespace)
```

For MCOA, this resource will no longer be used, and is replaced with PrometheusRule  and ScrapeConfig configs. The equivalent ScrapeConfig for the allowlist above is the following (can change jobName as desired):

```
apiVersion: monitoring.rhobs/v1alpha1
kind: ScrapeConfig
spec:
  jobName: some-job-name
  metricsPath: /federate
  params:
    match[]:
    - '{__name__="up"}'
    - '{__name__="container_memory_cache",container!=""}'
    # Don't forget to add the recording rule name you want to collect
    - '{__name__="container_memory_rss:sum"}'
```

 The equivalent PrometheusRule  for the allowlist above is the following (can change group name as desired):

```
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: my-rules-group
    rules:
      - record: container_memory_rss:sum
        expr: sum(container_memory_rss) by (container, namespace)
```

To simplify the transition to ScrapeConfig and PrometheusRule  from the custom allowlist, you can download a binary executable, input your custom allowlist, and it outputs the equivalent ScrapeConfig and PrometheusRule. To download this executable, first open the openshift console. Then at the top right click the question mark logo. From the dropdown menu, select **Command Line Tools**.   
![][image2]  
On this page, scroll down until you find the section **Advanced Cluster Management Observability Migration Tool \- latest.** Select the link to the download that matches OS and architecture.  
![][image3]  
Once downloaded, execute the following to generate your ScrapeConfig  and PrometheusRule yaml files.

```
/path/to/migration allowlist.yaml output/dir
```

Add the new config files to the hub cluster.

```
oc apply -f <output/dir>/custom-prometheusrule.yaml -n open-cluster-management-observability
oc apply -f <output/dir>/custom-scrapeconfig.yaml -n open-cluster-management-observability
```

Then add the ScrapeConfig  and PrometheusRule to the ClusterManagementAddOn resource.

```
kubectl patch clustermanagementaddon multicluster-observability-addon --type=json -p='[
{
   "op": "add",
   "path": "/spec/installStrategy/placements/0/configs/-",
   "value": {
      "group": "monitoring.rhobs",
      "resource": "scrapeconfigs",
      "name": "custom-scrapeconfig",
      "namespace": "open-cluster-management-observability"
   }
},
{
   "op": "add",
   "path": "/spec/installStrategy/placements/0/configs/-",
   "value": {
      "group": "monitoring.coreos.com",
      "resource": "prometheusrules",
      "name": "custom-prometheusrule",
      "namespace": "open-cluster-management-observability"
   }
}
]'
```

Once added, you should now be able to verify that your custom metrics are being collected through querying grafana or perses UI. For example, if in your custom ScrapeConfig matches the metric `up`, you can query for `up{job="my-app"}` to verify the ScrapeConfig is being used. For PrometheusRule, if you have a recording rule for `avg_response_time` you can quickly verify it is working by running a query `avg_response_time`. Should also check that any alerts or dashboards that use these custom metrics are now being populated.

The instructions for applying the new ScrapeConfig and PrometheusRule can also be found in the readme of the git repo [https://github.com/stolostron/allowlist-migration-mcoa](https://github.com/stolostron/allowlist-migration-mcoa). 

## The AddonDeploymentConfig {#the-addondeploymentconfig}

The following settings are currently supported for configuring the addon:

* `agentInstallNamespace`  
* `nodePlacement` with the associated `nodeSelector` and `tolerations`  
* `proxyConfig` limited to the `httpProxy` and `noProxy` configurations

Some settings such as the `nodeSelector` can be configured both in the AddonDeploymentConfig and in the PrometheusAgents APIs. The AddonDeploymentConfig values take precedence over direct modifications of the other resources.

The remaining settings will be supported in future versions of ACM Observability.

| ⚠️A single AddonDeploymentConfig is currently supported for all placements. I.e. the same instance must be referenced in all placements.  |
| :---- |

# Common configurations {#common-configurations}

## Sampling rate {#sampling-rate}

You can set the sampling rate for each `ScrapeConfig` by configuring its `scrapeInterval`. Otherwise the default set in the prometheusAgent resource is used (300s by default). 

Note that intervals below 90 seconds may result in `Error on ingesting out-of-order samples` errors in the Prometheus Agent. This occurs because some federated metrics have a lower resolution than the `scrapeInterval`, causing duplicate values to be resent and the associated error. The rest of the payload is ingested normally.

## Adding Custom Metrics {#adding-custom-metrics}

To add your own custom metrics, follow these steps:

1. **Create a ScrapeConfig:** In the `open-cluster-management-observability` namespace, create a `ScrapeConfig` that includes the required fields as detailed in the [common configuration](#common-configuration) section. Make sure you use the `monitoring.rhobs` resource group.  This should include the `jobName`, `metricsPath`, and `params`.  
2. **Add the Correct Label:** Add the appropriate label value for `app.kubernetes.io/component`:  
   * `platform-metrics-collector`: For platform metrics.  
   * `user-workload-metrics-collector`: For user workload metrics.  
3. **Configure Placement:** Add the configuration reference in the placements of the `ClusterManagementAddon` where you want the resource to be used.

The new `ScrapeConfig` will then be automatically deployed to the relevant managed clusters. The Prometheus Operator on each spoke will detect the new configuration and add it to the Prometheus Agent's configuration.

| ⚠️Make sure you reference only once each federated metric across all the ScrapeConfigs deployed on a given managed cluster otherwise you’ll get conflict “out of order errors” as they will be federated once for each ScrapeConfig  |
| :---- |

## User Workloads and ScrapeConfig Namespaces {#user-workloads-and-scrapeconfig-namespaces}

User workload scrapeconfigs can be created:

*  Either from the hub and the metrics will be collected in all the namespaces of the target managed clusters;  
* Or directly on the spoke cluster:  
  * If the scrapeConfig is deployed in the same namespace as the Prometheus Agent it applies to all namespaces. I.e. it will collect the referenced metrics in all namespaces.  
  * If the scrapeConfig is deployed in a specific namespace, it will only collect metrics coming from it, enforcing the namespace label on the collecting metrics.

You can also limit the namespaces watched by the Prometheus Agent by configuring the `scrapeConfigNamespaceSelector` value. For example, to restrict user workload scrapeConfigs to the namespaces containing the label `app=my-app` you would set:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: PrometheusAgent
spec:
  scrapeConfigNamespaceSelector:    matchLabels:
      app: my-app
```

## Federating User Workloads from CMO {#federating-user-workloads-from-cmo}

This is the default mode. Prerequisites:

* User workload monitoring is enabled on the managed cluster   
* User workload monitoring is enabled in the MultiClusterObservability custom resource  
* You have created scrapeConfigs with the expected label   
* The scrapeConfigs are referenced in the configurations list of the ClusterManagementAddOn for the target placements.

## Federating User Workloads from COO {#federating-user-workloads-from-coo}

Ensure that all prerequisites from the [previous section](#federating-user-workloads-from-cmo) are met. Next, update the scrape configuration to integrate the Prometheus service endpoint as configured by the Cluster Operator. For instance, consider the deployment of the following MonitoringStack:

```
kind: MonitoringStack
apiVersion: monitoring.rhobs/v1alpha1
metadata:
  name: my-monitoring-stack
  namespace: my-monitoring-ns
spec:
  ...
```

A service named after the MonitoringStack name is automatically created. We can use it in our scrapeConfig configuration:

```
apiVersion: monitoring.coreos.com/v1alpha1
kind: ScrapeConfig
spec:
  scrapeClass: “” 
  scheme: HTTP
  staticConfigs:
  - targets:
    - my-monitoring-stack.my-monitoring-ns.svc:9090
```

If a proxy is used with the Prometheus server, you can modify the ScrapeConfig to include TLS configuration. In this scenario, create a corresponding scrapeClass on the user workload PrometheusAgent and then reference it within the ScrapeConfig.

## Adapting the Default Metrics {#adapting-the-default-metrics}

You can use relabelling configurations to modify the metrics being collected. They can be added:

* Either in each individual scrapeConfig  
* Or globally at the remoteWrite configuration on the prometheusAgent.

For example, you can remove the Watchdog alert metric: 

* Either by adding a `metricRelabelings` in the platform-metrics-alerts scrapeConfig, where this metric collections is defined, with the benefit that it won’t reach the prometheus agent;  
* Or in the acm-observability `remoteWrite` configuration of the prometheus agent itself by adding a `writeRelabelConfigs`. It has effect after it was federated but before it is sent to the hub.

```
    - action: drop
      regex: ^Watchdog$
      sourceLabels:
        - alertname
```

## Exporting Metrics to External Endpoints {#exporting-metrics-to-external-endpoints}

In addition to the already existing methods to export metrics to external endpoints by configuring a `writeStorage` in MultiClusterObservability custom resource, you can configure custom remote write configurations to the deployed PrometheusAgents. Here is how the two methods differ:

* When you add a `writeStorage` to the MultiClusterObservability custom resource, the metrics received on the hub by the Observatorium API are forwarded to the configured external endpoints in addition to the Thanos Receivers.  
* When you configure a `remoteWrite` configuration in the PrometheusAgent, the metrics are directly sent by the managed cluster to the external endpoint. 

The new method offers the following advantages:

* **Configurable Metrics Forwarding:** Metrics can be filtered using relabeling rules.  
* **Enhanced Resiliency:** The system can withstand network partitions between the managed cluster and the external endpoint for up to two hours.

To configure the Prometheus Agent with an external endpoint, you need to create the necessary TLS communication secrets or configMaps within the `open-cluster-management-observability` namespace. After creating these secrets, add the `remoteWrite` configuration. For instance, the following example demonstrates how to export the "up" metric to a custom endpoint:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: PrometheusAgent
metadata:
  name: mcoa-default-platform-metrics-collector-global
  namespace: open-cluster-management-observability
spec:
  secrets:
   # Add the needed secrets
    - custom-endpoint-ca
    - custom-endpoint-cert
  remoteWrite:
    # Add your custom remote write config
    - name: custom-endpoint
      tlsConfig:
        caFile: /etc/prometheus/secrets/custom-endpoint-ca/ca.crt
        certFile: /etc/prometheus/secrets/custom-endpoint-cert/tls.crt
        keyFile: /etc/prometheus/secrets/custom-endpoint-cert/tls.key
      url: 'https://my-custom-remote-write-endpoint.io/api/v1/receive'
      writeRelabelConfigs:
        - action: keep
          regex: ^up$
          sourceLabels:
            - __name__
    - name: acm-observability
      ...

```

# Monitoring the Addon {#monitoring-the-addon}

The addon health is reported through the standard Open Cluster Management AddOn conditions on the ManagedClusterAddOn resource. They are displayed in the “All Clusters” view of the OCP console for each managed cluster. The status will be degraded if some resources are not deployed or the platform prometheus agent is not running.

On top of that, the following alerting rules are pushed to all managed clusters:

* **MetricsCollectorNotIngestingSamples**: This fires when the prometheus agent is not federating any metric.  
* **MetricsCollectorRemoteWriteFailures**: It fires when the prometheus agent has a high failure rate on remote write requests to the hub.  
* **MetricsCollectorRemoteWriteBehind**: It fires when the prometheus agent remote write is too slow, possibly because of network issues or a struggling hub receiver.

# COO Compatibility {#coo-compatibility}

MCOA utilizes the existing `obo-prometheus-operator` from COO on a managed cluster to reconcile Prometheus custom resources. If `obo-prometheus-operator` is not present, MCOA deploys it within the configured `agentInstallNamespace`. Both MCOA and COO share the `monitoring.rhobs` API Group for their `ScrapeConfig` and `PrometheusAgent` resources.

# Non OCP Platforms Support {#non-ocp-platforms-support}

MCOA supports non Openshift managed clusters. In addition of the resources deployed in OCP clusters it adds:

* The Node Exporter  
* Kube State Metrics  
* A Prometheus server

Alert forwarding is automatically enabled when the AddonDeploymentConfig contains the metricsAlertManagerHostname key in the customizedVariables.

| ⚠️The cluster ID of non OCP managed clusters now uses the [id.k8s.io](http://id.k8s.io) claim of the managed cluster while the current endpoint operator uses the cluster name. |
| :---- |

# Alert forwarding in MCOA {#alert-forwarding-in-mcoa}

By default, MCOA doesn’t configure alert forwarding from OCP managed clusters Prometheus’ to the Hub Alertmanager. This can however be accomplished by adding a policy which configures this configuration. To do so for platform metrics, the following yaml can be used.

```
apiVersion: policy.open-cluster-management.io/v1
kind: Policy
metadata:
  name: mcoa-alert-forward-platform
  namespace: open-cluster-management-global-set
spec:
  disabled: false
  policy-templates:
  - objectDefinition:
      apiVersion: policy.open-cluster-management.io/v1
      kind: ConfigurationPolicy
      metadata:
        name: mcoa-alert-forward-platform
      spec:
        namespaceSelector:
          exclude:
          - kube-*
          include:
          - default
        object-templates-raw: |
          {{ $hubBaseDomain:= "INPUT_BASE_DOMAIN" }}
          {{ $hubName := (split "." $hubBaseDomain)._0 }}

          ## Get the current ConfigMap and read the value as a yaml structure
          {{- $cmo := (lookup "v1" "ConfigMap" "openshift-monitoring" "cluster-monitoring-config") }}
          {{- $cy := dict }}
          {{- if and $cmo $cmo.data }}
            {{- $cy = (index $cmo "data" "config.yaml") | fromYaml }}
          {{- end }}

          ## define what we want the config to include
          {{- $mangedConfig := dict }}

          {{- $pm := `
            prometheusK8s:
              additionalAlertmanagerConfigs:
              - apiVersion: v2
                bearerToken:
                  key: token
                  name: observability-alertmanager-accessor-%[1]s
                scheme: https
                staticConfigs:
                - alertmanager-open-cluster-management-observability.apps.%[2]s
                tlsConfig:
                  ca:
                    key: service-ca.crt
                    name: hub-alertmanager-router-ca-%[1]s
                  insecureSkipVerify: false
              externalLabels:
                managed_cluster: %[3]s
          ` }}

          ## merge all the config into one
          {{- $mangedConfig = merge $mangedConfig
                              ((printf $pm $hubName $hubBaseDomain (fromClusterClaim "id.openshift.io"))| fromYaml)
          }}
          - complianceType: mustonlyhave
            objectDefinition:
              apiVersion: v1
              data:
                config.yaml: |
                  {{ (merge $cy $mangedConfig)| toYaml |autoindent }}
              kind: ConfigMap
              metadata:
                name: cluster-monitoring-config
                namespace: openshift-monitoring
            recordDiff: InStatus
  remediationAction: enforce
---
apiVersion: policy.open-cluster-management.io/v1
kind: PlacementBinding
metadata:
  name: mcoa-alert-forward-platform-placement
  namespace: open-cluster-management-global-set
placementRef:
  apiGroup: cluster.open-cluster-management.io
  kind: Placement
  name: global
subjects:
- apiGroup: policy.open-cluster-management.io
  kind: Policy
  name: mcoa-alert-forward-platform
```

To apply this policy, first ensure that the \`$hubBaseDomain\` is filled in with the appropriate base domain for the ACM hub. Then apply the policy with \`oc apply \-f ./forward-platform-alerts.yaml\`.   
The policy above is in \`inform\` mode. This allows double checking the changes the policy will make across the managed clusters. In the OCP console, go to Fleet Management, Governance, Policies, to see the policy and the changes it will make.

The policy takes the existing configmap as input and should retain any customizations done, after the policy is applied. One exception (**note?)** is if there are custom changes made to the \`additionalAlertmanagerConfigs\` part of the configmap. In that case incorporate those changes directly into the policy, before applying the policy.

After having validated the changes, change the \`remediationAction\` in the yaml above, to \`enforce\` and apply the policy again. This will roll out the changes to the configmap across all managed clusters, and enable alert forwarding from these to the ACM Hub.

**Note:** the policy above is placed in \`open-cluster-management-global-set\`. If you have non OCP managed clusters you need to make sure a placement is used, which excludes these.

For forwarding alerts from the User Workload Metrics stack, the below policy can be used, in the same way as the one for platform metrics.

```
apiVersion: policy.open-cluster-management.io/v1
kind: Policy
metadata:
  name: mcoa-alert-forward-uwl
  namespace: open-cluster-management-global-set
spec:
  disabled: false
  policy-templates:
  - objectDefinition:
      apiVersion: policy.open-cluster-management.io/v1
      kind: ConfigurationPolicy
      metadata:
        name: mcoa-alert-forward-uwl
      spec:
        namespaceSelector:
          exclude:
          - kube-*
          include:
          - default
        object-templates-raw: |
          {{ $hubBaseDomain:= "INPUT_BASE_DOMAIN" }}
          {{ $hubName := (split "." $hubBaseDomain)._0 }}

          ## Get the current ConfigMap and read the value as a yaml structure
          {{- $cmo := (lookup "v1" "ConfigMap" "openshift-user-workload-monitoring" "user-workload-monitoring-config") }}
          {{- $cy := dict }}
          {{- if and $cmo $cmo.data }}
            {{- $cy = (index $cmo "data" "config.yaml") | fromYaml }}
          {{- end }}

          ## define what we want the config to include
          {{- $mangedConfig := dict }}

          {{- $pm := `
            prometheus:
              additionalAlertmanagerConfigs:
              - apiVersion: v2
                bearerToken:
                  key: token
                  name: observability-alertmanager-accessor-%[1]s
                scheme: https
                staticConfigs:
                - alertmanager-open-cluster-management-observability.apps.%[2]s
                tlsConfig:
                  ca:
                    key: service-ca.crt
                    name: hub-alertmanager-router-ca-%[1]s
                  insecureSkipVerify: false
              externalLabels:
                managed_cluster: %[3]s
          ` }}

          ## merge all the config into one
          {{- $mangedConfig = merge $mangedConfig
                              ((printf $pm $hubName $hubBaseDomain (fromClusterClaim "id.openshift.io"))| fromYaml)
          }}
          - complianceType: mustonlyhave
            objectDefinition:
              apiVersion: v1
              data:
                config.yaml: |
                  {{ (merge $cy $mangedConfig )| toYaml |autoindent }}
              kind: ConfigMap
              metadata:
                name: user-workload-monitoring-config
                namespace: openshift-user-workload-monitoring
            recordDiff: InStatus
  remediationAction: enforce
---
apiVersion: policy.open-cluster-management.io/v1
kind: PlacementBinding
metadata:
  name: mcoa-alert-forward-uwl-placement
  namespace: open-cluster-management-global-set
placementRef:
  apiGroup: cluster.open-cluster-management.io
  kind: Placement
  name: global
subjects:
- apiGroup: policy.open-cluster-management.io
  kind: Policy
  name: mcoa-alert-forward-uwl
```

# Grafana {#grafana}

MCOA's platform metrics have undergone a comprehensive review and optimization to enhance observability while minimizing cardinality and maximizing performance. As a result, platform dashboards have been subtly updated to incorporate new expressions where appropriate. For backward compatibility, new dashboards are located in a dedicated "Platform \- MCOA" directory, while deprecated dashboards are marked with "DEPRECATED." The updated set of dashboards now includes networking dashboards.

# FAQ {#faq}

## Migrating your Custom Allow-List ConfigMaps {#migrating-your-custom-allow-list-configmaps}

This only applies to your **custom** allow-list. Standard platform metrics, essential for the operation of default platform dashboards, are collected automatically.

The `metrics allowlist` configmap is organized into several sections:

* **Names:** Metric names can be added to the `params.match[]` list of the ScrapeConfig using the match syntax (see example below).  
* **Matches:** These utilize the same syntax as `scrapeConfig`, requiring only the addition of curly braces.  
* **Renames:** This feature is not supported.  
* **Recording\_rules:** Implement these using the `prometheusRule` API, maintaining the same syntax.  
* **Collect\_rules:** This feature is not supported.

Metrics allow list example:

```
kind: ConfigMap
apiVersion: v1
data:
  metrics_list.yaml: |
    names:
      - up
    matches:
      - __name__="container_memory_cache",container!=""
    recording_rules:
      - record: container_memory_rss:sum
        expr: sum(container_memory_rss) by (container, namespace)
```

Corresponding ScrapeConfig configuration:

```
apiVersion: monitoring.rhobs/v1alpha1
kind: ScrapeConfig
spec:
  jobName: some-job-name
  metricsPath: /federate
  params:
    match[]:
    - '{__name__="up"}'
    - '{__name__="container_memory_cache",container!=""}'
    # Don't forget to add the recording rule name you want to collect
    - '{__name__="container_memory_rss:sum"}'
```

Corresponding PrometheusRule configuration:

```
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: my-rules-group
    rules:
      - record: container_memory_rss:sum
        expr: sum(container_memory_rss) by (container, namespace)
```

## Resiliency to Network Partitions with the Hub {#resiliency-to-network-partitions-with-the-hub}

**How Data Buffering Works**  
The Prometheus Agent uses a Write Ahead Log (WAL) to store federated samples on disk. This ensures that if network connectivity is lost, data is preserved locally until it can be re-sent.

**Ingestion Constraints on the Hub (Thanos)**  
When connectivity is restored, the Hub (Thanos Receiver) attempts to ingest this buffered data. However, there are specific constraints:

1. **Block Duration:** Thanos builds data blocks with a **2-hour duration**. Once a block is completed, it becomes immutable, meaning new samples cannot be added to it. Samples older than the start time of the current block are rejected.  
2. **Single Stream Limitation**: Because we utilize a single block stream, a managed cluster cannot send data that is more than **1 hour older** than the most recent sample received from **any** managed cluster.

Note: The rejection of older samples could be mitigated by enabling the tsdb.out-of-order.time-window flag on the Receiver. This allows samples to be added to older blocks, though this configuration is not currently active.

**Summary of Data Ingestion Outcomes**  
Assuming the buffered samples are less than 1 hour older than the global most recent sample (meeting the stream prerequisite), the outcome depends on the age of the block currently being built:

* **Scenario A: Safe Ingestion**  
  If the current block is **between 1 and 2 hours old**, all buffered samples will fall within the current block's time window and be ingested correctly.  
* **Scenario B: Data Loss (Gaps)**  
  If the current block is **less than 1 hour old** (e.g., created 30 minutes ago), the system can only accept samples dating back to the start of this block. Any data older than the block's start time will be rejected, resulting in a gap in metrics for that cluster.

## Can a Managed Cluster Belong to Multiple Placements?  {#can-a-managed-cluster-belong-to-multiple-placements?}

A managed cluster can only be associated with a single placement from those referenced in the `ClusterManagementAddon`. If a managed cluster is part of multiple placements, it will inherit the configuration from the last compatible placement listed in the `ClusterManagementAddon`. You can verify the applied configuration in the `ManagedClusterAddOn`.

## Disabling Metrics Collection on a Specific Cluster {#disabling-metrics-collection-on-a-specific-cluster}

If you want to disable metrics collection on a given managed cluster, you must exclude if from all placements referenced in the ClusterManagementAddOn. This can be done by setting a label selector on the clusterID such as:

```
apiVersion: cluster.open-cluster-management.io/v1beta1
kind: Placement
metadata:
  name: my-placement
  namespace: open-cluster-management-global-set
spec:
  clusterSets:
    - global
  predicates:
    - requiredClusterSelector:
        claimSelector:
          matchExpressions:
            - key: id.k8s.io
              operator: NotIn
              values:
                - 96ae3c00-666b-4579-a39c-497fc0173d5d # the cluster id
```

## Troubleshooting Custom Metrics Collection {#troubleshooting-custom-metrics-collection}

If your custom `scrapeConfig` isn't collecting metrics, use the following checklist to troubleshoot the issue:

1. Verify that the `scrapeConfig` includes the correct platform or user workload label.  
2. For user workloads, confirm that user workload monitoring is configured in MCO on both the hub and managed clusters.  
3. Ensure the configuration is referenced in the `ClusterManagementAddOn` target placement.  
4. Check that the `specHash` is generated within `ClusterManagementAddOn.status.installProgressions.configReferences` for the `scrapeConfig`. If it's missing, the resources don't exist.  
   Additionally, use a command similar to the one provided to check if the manifestWork for the target cluster contains the update.

```
oc get manifestworks -n spoke-a | grep observability | cut -d " " -f1 | xargs -I {} oc get manifestworks/{} -n spoke-a -o yaml | grep -A3 -B3 my-update
```

Another command to retrieve the feedbackRules used to report the health state on a managedCluster:

```
oc get manifestwork -n local-cluster -o name | grep -i obs | xargs oc get -o yaml -n local-cluster | yq '.items[].status.resourceStatus.manifests[] | select(.statusFeedback.values | length > 0) | del(.conditions)'
```

5. Confirm the scrape config is deployed in the Managed cluster within the `agentInstallNamespace`. If it's missing, check the addon manager logs for errors. If nothing is obvious, you can try restarting it by deleting it to trigger new reconciliations.  
6. Examine the logs of the Prometheus agent (platform or user workload) to ensure it can federate metrics from the in-cluster Prometheus and forward them to the hub.  
7. Validate that the metric exists in the Prometheus server on the managed cluster from which the metrics are being federated. You can use the Observe Metrics section of the OCP console for platform metrics.

## Deploying the AddOn Configuration Changes Progressively {#deploying-the-addon-configuration-changes-progressively}

You can customize how updated configurations are deployed to managed clusters within a placement by configuring the [rollout strategy](https://open-cluster-management.io/docs/getting-started/installation/addon-management/#rollout-strategy). The default strategy, "All," deploys updates to all managed clusters simultaneously.

For enhanced safety, a progressive rollout strategy can be defined. This allows you to precisely control which group of clusters receives the update first, as well as the rate at which the remaining managed clusters are updated.

## Avoiding Reconciliation of Unavailable Clusters {#avoiding-reconciliation-of-unavailable-clusters}

To prevent wasting resources, exclude unreachable or unavailable managed clusters from placements. These clusters are automatically tainted:

```
apiVersion: cluster.open-cluster-management.io/v1
kind: ManagedCluster
spec:
  taints:
    - effect: NoSelect
      key: cluster.open-cluster-management.io/unreachable
      timeAdded: '2025-10-15T10:15:11Z'
```

Make sure you remove the corresponding toleration in the placements when they are set:

```
apiVersion: cluster.open-cluster-management.io/v1beta1
kind: Placementspec:
  tolerations:
    - key: cluster.open-cluster-management.io/unreachable
      operator: Equal
    - key: cluster.open-cluster-management.io/unavailable
      operator: Equal
```

## Creating a Placement for Single Node Openshift Spokes {#creating-a-placement-for-single-node-openshift-spokes}

The objective is to create a specific placement for Single Node OpenShift (SNO) spokes. This will allow us to tailor metrics collection and allocate the minimum necessary resources to the Prometheus Agent for these spokes.

The first step is to identify and select these managed clusters from the global `ManagedClusterSet`. This is done by using placement predicates. In this example, we select ManagedClusters with the label `vendor: OpenShift` and the claim with name `controlplanetopology.openshift.io` and value `SingleReplica`.

```
apiVersion: cluster.open-cluster-management.io/v1beta1
kind: Placement
metadata:
  name: sno
  namespace: open-cluster-management-global-set
spec:
  clusterSets:
    - global
  predicates:
    - requiredClusterSelector:
        labelSelector:
          matchLabels:
            vendor: OpenShift
    - requiredClusterSelector:
        claimSelector:
          matchExpressions:
            - key: controlplanetopology.openshift.io
              operator: In
              values:
                - SingleReplica
```

| ⚠️We are creating the `Placement` in the `open-cluster-management-global-set` namespace because it already contains a `ManagedClusterSetBinding` for the `global` `ManagedClusterSet`. This allows us to manage it with a `Placement`. This projection of `ManagedClusterSets` into namespaces is used to restrict permissions to manage a given set. |
| :---- |

We can verify the placement's functionality by checking the `status.numberOfSelectedClusters` field in the `PlacementDecision` status, which should be greater than 0\.

You can examine the details of the selected clusters in the referenced `PlacementDecision` within `status.decisionGroups[].decisions`.

The next step is to reference this placement in the `ClusterManagementAddon` named `multicluster-observability-addon`:

```
spec:
  installStrategy:
    placements:
      - name: sno
        namespace: open-cluster-management-global-set
```

MCOA will then automatically create new Prometheus Agents for this placement in the `open-cluster-management-observability` namespace.

You can then modify the `PrometheusAgent` to, for example, reduce the requested CPU, and these changes will be automatically applied to the target managed clusters.

# Annexes {#annexes}

## The Placement API – Basics {#the-placement-api-–-basics}

The [placement API](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.13/html-single/clusters/index#placement-intro) ([upstream documentation](https://open-cluster-management.io/docs/concepts/content-placement/placement/)) is used to decide what resources to deploy on which clusters and how. It acts as a multicluster scheduler. While the [ManagedClusterSet API](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.13/html-single/clusters/index#managedclustersets-intro) ([upstream documentation](https://open-cluster-management.io/docs/concepts/cluster-inventory/managedclusterset/)) is used to manage access to your managed clusters by assigning RBAC to your ManagedClusterSets. 

| ⚠️The Red Hat implementation might differ in certain aspects from the upstream version. For example, ManagedClusters can only be assigned to a single ManagedClusterSet using the `ExclusiveClusterSetLabel` (not the `LabelSelector`) because Red Hat ACM uses the `ManagedClusterSet` for RBAC control. |
| :---- |

Here's a diagram illustrating the relationship between the different custom resources used for placing resources on managed clusters:

![][image4]

To better understand the API's capabilities, we'll explore use cases related to ACM observability.  
For more detailed information, refer to the official documentation.  
By default, a placement called Global, (which includes all managed clusters) is used to deploy MCOA resources on spokes.
