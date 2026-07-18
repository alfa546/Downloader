import { useState, useEffect } from 'react'
import { Video, AlertCircle, Loader2, Download, Settings, ChevronRight } from 'lucide-react'
import './App.css'

function App() {
  const [url, setUrl] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [removeWatermark, setRemoveWatermark] = useState(true)
  const [quality, setQuality] = useState('1080p')

  const statusMap: Record<string, string> = {
    'queued': 'Queued for downloading...',
    'downloading': 'Downloading video...',
    'removing_watermark': 'Removing watermark...',
    'awaiting_quality_choice': 'Ready for finalization',
    'queued_for_processing': 'Preparing to process...',
    'resizing': 'Applying fast-path resize...',
    'upscaling': 'AI Upscaling in progress...',
    'done': 'Process complete!',
    'failed': 'Process failed.'
  }

  const submitJob = async () => {
    if (!url) return;
    setError(null)
    setStatus('submitting')
    try {
      const res = await fetch('http://localhost:8000/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, remove_watermark: removeWatermark })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail?.[0]?.msg || data.detail || 'Error submitting job')
      setJobId(data.job_id)
      setStatus(data.status)
    } catch (err: any) {
      setError(err.message)
      setStatus('')
    }
  }

  useEffect(() => {
    let interval: number;
    if (jobId && status !== 'done' && status !== 'failed' && status !== 'awaiting_quality_choice') {
      interval = window.setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/jobs/${jobId}/status`)
          const data = await res.json()
          setStatus(data.status)
          setProgress(data.progress ?? null)
          if (data.status === 'failed') setError(data.error)
          if (data.status === 'awaiting_quality_choice') {
             setShowModal(true)
          }
        } catch (err) {
          console.error(err)
        }
      }, 2000)
    }
    return () => clearInterval(interval)
  }, [jobId, status])

  const finalizeJob = async () => {
    setShowModal(false)
    try {
      const res = await fetch(`http://localhost:8000/jobs/${jobId}/finalize?quality=${quality}`, {
        method: 'POST'
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error finalizing job')
      setStatus(data.status)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const getStepStatus = (stepKey: string) => {
    const statusOrder = ['queued', 'downloading', 'removing_watermark', 'awaiting_quality_choice', 'queued_for_processing', 'resizing', 'upscaling', 'done'];
    const currentIndex = statusOrder.indexOf(status);
    
    if (status === 'failed') return 'failed';
    
    if (stepKey === 'processing') {
      const isProcessingStep = status === 'queued_for_processing' || status === 'resizing' || status === 'upscaling';
      if (isProcessingStep) return 'active';
      const hasPassed = currentIndex > statusOrder.indexOf('upscaling');
      return hasPassed ? 'completed' : 'pending';
    }
    
    const stepIndex = statusOrder.indexOf(stepKey);
    if (currentIndex > stepIndex) return 'completed';
    if (currentIndex === stepIndex) return 'active';
    return 'pending';
  }

  const steps = [
    { key: 'queued', label: 'Queued in pipeline' },
    { key: 'downloading', label: 'Downloading video' },
    { key: 'removing_watermark', label: 'Removing watermark' },
    { key: 'processing', label: 'Formatting & finalizing' },
    { key: 'done', label: 'Ready to play' }
  ]

  return (
    <div className="app-container">
      <Video size={48} className="logo-icon" />
      <h1>MediaForge</h1>
      <p className="subtitle">Download, clean, and upscale videos from TikTok, Instagram, YouTube, and Facebook.</p>
      
      <div className="input-group">
        <input 
          type="text" 
          value={url} 
          onChange={e => setUrl(e.target.value)} 
          placeholder="Paste video URL here..."
          disabled={isProcessing}
        />
        <button onClick={submitJob} disabled={isProcessing || !url}>
          {isProcessing ? <Loader2 className="animate-spin" /> : <ChevronRight />}
          Process
        </button>
      </div>

      <div className="options-container">
        <label className="toggle-label">
          <input 
            type="checkbox" 
            className="modern-checkbox"
            checked={removeWatermark} 
            onChange={e => setRemoveWatermark(e.target.checked)} 
            disabled={isProcessing}
          />
          <span className="toggle-text">Remove Watermark</span>
        </label>
      </div>

      {error && (
        <div className="error-message">
          <AlertCircle size={20} />
          {error}
        </div>
      )}
      
      {status && status !== 'submitting' && (
        <div className="status-card">
          <div className="status-header">
            {isProcessing && <Loader2 className="animate-spin" size={20} />}
            {statusMap[status] || status}
          </div>
          
          {progress !== null && status === 'upscaling' && (
            <div className="progress-container">
              <div className="progress-info">
                <span>AI Upscaling Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="progress-bar-bg">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
          )}

          {/* Real-time Progress Stepper */}
          <div className="stepper-container">
            {steps.map((step) => {
              const stepState = getStepStatus(step.key);
              return (
                <div key={step.key} className={`step-item ${stepState}`}>
                  <div className="step-indicator">
                    {stepState === 'completed' && '✓'}
                    {stepState === 'active' && '●'}
                    {stepState === 'pending' && '○'}
                    {stepState === 'failed' && '✗'}
                  </div>
                  <span className="step-label">{step.label}</span>
                </div>
              );
            })}
          </div>

          {status === 'done' && (
            <div className="result-container">
              <video 
                src={`http://localhost:8000/jobs/${jobId}/download`} 
                controls 
                className="video-player"
              />
              <a href={`http://localhost:8000/jobs/${jobId}/download`} className="download-btn" download>
                <Download size={20} />
                Download Final Video
              </a>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3><Settings size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }}/> Output Quality</h3>
            <select value={quality} onChange={e => setQuality(e.target.value)}>
              <option value="480p">480p (Fast)</option>
              <option value="720p">720p (Standard)</option>
              <option value="1080p">1080p (HD)</option>
              <option value="4k">4K (AI Upscale - Slow)</option>
            </select>
            <button onClick={finalizeJob}>
              Confirm Selection
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
