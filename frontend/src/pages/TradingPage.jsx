import TradingPanel from '../components/TradingPanel'

export default function TradingPage({ initialSymbol = '', onAskAI }) {
  return (
    <div className="h-full overflow-hidden animate-in fade-in duration-300">
      <TradingPanel initialSymbol={initialSymbol} onAskAI={onAskAI} />
    </div>
  )
}
