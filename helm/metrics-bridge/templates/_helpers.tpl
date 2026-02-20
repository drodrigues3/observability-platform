{{- define "metrics-bridge.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "metrics-bridge.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "metrics-bridge.labels" -}}
helm.sh/chart: {{ include "metrics-bridge.name" . }}-{{ .Chart.Version }}
{{ include "metrics-bridge.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "metrics-bridge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "metrics-bridge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: metrics-bridge
{{- end }}

{{- define "metrics-bridge.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "metrics-bridge.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
