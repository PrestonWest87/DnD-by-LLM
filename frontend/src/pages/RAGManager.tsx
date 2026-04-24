import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useAuthStore } from '../lib/store'
import { FileText, Upload, Search, Book, Sparkles, Settings, Check } from 'lucide-react'

interface CustomRule {
  id: number
  title: string
  source: string
  content: string
}

interface SearchResult {
  type: string
  data: any
}

export default function RAGManager() {
  const { id: campaignId } = useParams()
  const { token } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'browse' | 'upload' | 'search'>('browse')
  const [rules, setRules] = useState<CustomRule[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  const [file, setFile] = useState<File | null>(null)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (campaignId) {
      loadRules()
    }
  }, [campaignId])

  const loadRules = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`/api/rag/custom/search?query=a&campaign_id=${campaignId}&limit=50`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setRules(data)
      }
    } catch (err) {
      console.error('Failed to load rules:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!file || !campaignId) return
    
    setUploading(true)
    setError('')
    setSuccess('')
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('campaign_id', campaignId)
    formData.append('content_type', 'rule')
    
    try {
      const response = await fetch('/api/rag/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })
      
      if (response.ok) {
        const data = await response.json()
        setSuccess(data.message)
        setFile(null)
        loadRules()
      } else {
        const data = await response.json()
        setError(data.detail || 'Upload failed')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleSearch = async () => {
    if (!query || !campaignId) return
    
    setSearching(true)
    setError('')
    
    try {
      const sources = 'rules,spells,custom'
      const response = await fetch(
        `/api/rag/search?query=${encodeURIComponent(query)}&campaign_id=${campaignId}&sources=${sources}&limit=5`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data)
      }
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Book className="w-8 h-8 text-primary" />
          <h1 className="font-display text-3xl font-bold">RAG Content Manager</h1>
        </div>
      </div>

      <div className="flex gap-4 border-b border-border">
        <button
          onClick={() => setActiveTab('browse')}
          className={`pb-3 px-4 flex items-center gap-2 ${activeTab === 'browse' ? 'border-b-2 border-primary text-primary' : 'text-textMuted'}`}
        >
          <Book className="w-4 h-4" />
          Browse Rules
        </button>
        <button
          onClick={() => setActiveTab('upload')}
          className={`pb-3 px-4 flex items-center gap-2 ${activeTab === 'upload' ? 'border-b-2 border-primary text-primary' : 'text-textMuted'}`}
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>
        <button
          onClick={() => setActiveTab('search')}
          className={`pb-3 px-4 flex items-center gap-2 ${activeTab === 'search' ? 'border-b-2 border-primary text-primary' : 'text-textMuted'}`}
        >
          <Search className="w-4 h-4" />
          Search
        </button>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-success/10 border border-success/20 text-success px-4 py-3 rounded-lg">
          {success}
        </div>
      )}

      {activeTab === 'browse' && (
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-4">Custom Rules</h2>
          
          {loading ? (
            <p className="text-textMuted">Loading...</p>
          ) : rules.length === 0 ? (
            <p className="text-textMuted">No custom rules uploaded yet.</p>
          ) : (
            <div className="space-y-4">
              {rules.map((rule) => (
                <div key={rule.id} className="p-4 bg-surfaceHover rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{rule.title}</h3>
                      <p className="text-sm text-textMuted">Source: {rule.source}</p>
                    </div>
                  </div>
                  <p className="text-sm mt-2 line-clamp-3">{rule.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'upload' && (
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-4">Upload Rule Book</h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm text-textMuted block mb-2">File (PDF, MD, TXT, JSON, HTML)</label>
              <input
                type="file"
                accept=".pdf,.md,.txt,.json,.html"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="input w-full"
              />
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="btn-primary flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'search' && (
        <div className="card p-6 space-y-4">
          <h2 className="text-xl font-semibold">Search Content</h2>
          
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search rules, spells, custom content..."
              className="input flex-1"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={!query || searching}
              className="btn-primary"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="space-y-4 mt-4">
              {searchResults.map((result, i) => (
                <div key={i} className="p-4 bg-surfaceHover rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    {result.type === 'srd_rule' && <FileText className="w-4 h-4 text-primary" />}
                    {result.type === 'spell' && <Sparkles className="w-4 h-4 text-accent" />}
                    {result.type === 'custom_rule' && <Book className="w-4 h-4 text-success" />}
                    <span className="text-xs uppercase text-textMuted">{result.type}</span>
                  </div>
                  <h3 className="font-semibold">{result.data.title || result.data.name}</h3>
                  <p className="text-sm mt-1">{result.data.content || result.data.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}