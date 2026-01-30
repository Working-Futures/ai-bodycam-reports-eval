import express from 'express'
import cors from 'cors'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import csv from 'csv-parser'
import { createReadStream } from 'fs'
import { Readable } from 'stream'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const PORT = process.env.PORT || 3001

// In production, serve static files from dist directory
// In development, we rely on Vite dev server
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, 'dist')))
}

app.use(cors())
app.use(express.json())

const DATA_DIR = path.join(__dirname, 'data')
const RESPONSES_DIR = path.join(__dirname, 'responses')

// Ensure responses directory exists
fs.mkdir(RESPONSES_DIR, { recursive: true }).catch(console.error)

// Load videos from CSV
async function loadVideos() {
  return new Promise(async (resolve, reject) => {
    try {
      // Read file and strip BOM
      let fileContent = await fs.readFile(path.join(DATA_DIR, 'videos.csv'), 'utf-8')
      // Remove UTF-8 BOM if present
      if (fileContent.charCodeAt(0) === 0xFEFF) {
        fileContent = fileContent.slice(1)
      }
      
      const videos = []
      Readable.from(fileContent)
        .pipe(csv({
          skipEmptyLines: true,
          skipLinesWithError: true
        }))
        .on('data', (row) => {
          // Skip empty rows
          if (row.VideoID && row.VideoID.trim()) {
            videos.push(row)
          }
        })
        .on('end', () => resolve(videos))
        .on('error', reject)
    } catch (error) {
      reject(error)
    }
  })
}

// Get video ID number from video ID string (e.g., "video_01" -> "01")
function getVideoNumber(videoId) {
  const match = videoId.match(/video_(\d+)/)
  if (!match) return null
  const num = parseInt(match[1], 10)
  // Use 2 digits for 1-99, 3 digits for 100+
  return num >= 100 ? num.toString() : num.toString().padStart(2, '0')
}

// Get narrative ID number from narrative ID string (e.g., "narrative_01" -> "01")
function getNarrativeNumber(narrativeId) {
  const match = narrativeId.match(/narrative_(\d+)/)
  if (!match) return null
  const num = parseInt(match[1], 10)
  // Use 2 digits for 1-99, 3 digits for 100+
  return num >= 100 ? num.toString() : num.toString().padStart(2, '0')
}

// API Routes

// Get all videos
app.get('/api/videos', async (req, res) => {
  try {
    const videos = await loadVideos()
    res.json(videos)
  } catch (error) {
    console.error('Error loading videos:', error)
    res.status(500).json({ error: 'Failed to load videos' })
  }
})

// Get narrative by ID
app.get('/api/narrative/:narrativeId', async (req, res) => {
  try {
    const { narrativeId } = req.params
    const narrativeNum = getNarrativeNumber(narrativeId)
    
    if (!narrativeNum) {
      return res.status(400).json({ error: 'Invalid narrative ID' })
    }
    
    const filePath = path.join(DATA_DIR, 'Narratives', `narrative_${narrativeNum}.txt`)
    
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      res.type('text/plain').send(content)
    } catch (error) {
      if (error.code === 'ENOENT') {
        res.status(404).json({ error: 'Narrative not found' })
      } else {
        throw error
      }
    }
  } catch (error) {
    console.error('Error loading narrative:', error)
    res.status(500).json({ error: 'Failed to load narrative' })
  }
})

// Get atomic facts by video ID
app.get('/api/atomic-facts/:videoId', async (req, res) => {
  try {
    const { videoId } = req.params
    const videoNum = getVideoNumber(videoId)
    
    if (!videoNum) {
      return res.status(400).json({ error: 'Invalid video ID' })
    }
    
    const filePath = path.join(DATA_DIR, 'Atomic Facts', `atomic_facts_${videoNum}.txt`)
    
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      const facts = content
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
      
      res.json({ facts })
    } catch (error) {
      if (error.code === 'ENOENT') {
        res.status(404).json({ error: 'Atomic facts not found' })
      } else {
        throw error
      }
    }
  } catch (error) {
    console.error('Error loading atomic facts:', error)
    res.status(500).json({ error: 'Failed to load atomic facts' })
  }
})

// Get all responses for a user
app.get('/api/responses/:username', async (req, res) => {
  try {
    const { username } = req.params
    const filePath = path.join(RESPONSES_DIR, `${username}.json`)
    
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      const responses = JSON.parse(content)
      res.json(responses)
    } catch (error) {
      if (error.code === 'ENOENT') {
        res.status(404).json({ error: 'No responses found' })
      } else {
        throw error
      }
    }
  } catch (error) {
    console.error('Error loading user responses:', error)
    res.status(500).json({ error: 'Failed to load user responses' })
  }
})

// Save response for a specific video
app.post('/api/responses/:username/:videoId', async (req, res) => {
  try {
    const { username, videoId } = req.params
    const responses = req.body
    
    const filePath = path.join(RESPONSES_DIR, `${username}.json`)
    
    // Load existing responses or create new object
    let allResponses = {}
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      allResponses = JSON.parse(content)
    } catch (error) {
      // File doesn't exist yet, that's okay
      if (error.code !== 'ENOENT') throw error
    }
    
    // Update with new response
    allResponses[videoId] = {
      ...responses,
      timestamp: new Date().toISOString()
    }
    
    // Save back to file
    await fs.writeFile(filePath, JSON.stringify(allResponses, null, 2), 'utf-8')
    
    res.json({ success: true })
  } catch (error) {
    console.error('Error saving response:', error)
    res.status(500).json({ error: 'Failed to save response' })
  }
})

// Catch all handler: send back to index.html for client-side routing (production only)
if (process.env.NODE_ENV === 'production') {
  app.get('*', (req, res) => {
    // Don't serve index.html for API routes
    if (req.path.startsWith('/api')) {
      return res.status(404).json({ error: 'API route not found' })
    }
    res.sendFile(path.join(__dirname, 'dist', 'index.html'))
  })
}

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`)
  if (process.env.NODE_ENV === 'production') {
    console.log('Production mode: serving static files from dist/')
  } else {
    console.log('Development mode: use Vite dev server for frontend')
  }
})
