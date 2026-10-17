import TermsGate from '../components/TermsGate'

export default function TermsPage({ onAccept, onDecline }) {
  return <TermsGate onAccept={onAccept} onDecline={onDecline} />
}
