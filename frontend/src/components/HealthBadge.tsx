interface Props {
  healthy: boolean | null
}

export default function HealthBadge({ healthy }: Props) {
  const label = healthy === null ? '检测中' : healthy ? '服务在线' : '服务离线'
  return (
    <span className={`health-badge ${healthy === true ? 'ok' : healthy === false ? 'down' : 'pending'}`}>
      <span className="dot" />
      {label}
    </span>
  )
}
