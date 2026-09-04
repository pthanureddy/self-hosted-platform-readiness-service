{{- define "readiness.name" -}}readiness-service{{- end }}
{{- define "readiness.labels" -}}
app.kubernetes.io/name: {{ include "readiness.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

