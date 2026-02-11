<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header with progress -->
    <div class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Bodycam Survey</h1>
            <p class="text-sm text-gray-600">User: {{ username }}</p>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <p class="text-sm font-medium text-gray-700">
                Progress: {{ completedCount }} / {{ totalVideos }} videos completed
              </p>
              <p class="text-xs text-gray-500">
                {{ remainingCount }} remaining
              </p>
            </div>
            <select
              v-if="sortedVideos.length > 0"
              :value="activeVideoId || ''"
              @change="goToVideo($event.target.value)"
              class="px-3 py-2 text-sm border border-gray-300 rounded-md bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 max-w-[200px]"
            >
              <option value="" disabled>Jump to video...</option>
              <option
                v-for="v in sortedVideos"
                :key="v.VideoID"
                :value="v.VideoID"
              >
                {{ isVideoSubmitted(v.VideoID) ? '✓' : '○' }} {{ v.VideoID }}
              </option>
            </select>
          </div>
          <button
            @click="handleLogout"
            class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Logout
          </button>
        </div>
        <div class="mt-4">
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: `${progressPercentage}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Survey Content -->
    <div v-if="loading" class="flex items-center justify-center min-h-[60vh]">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading survey...</p>
      </div>
    </div>

    <div v-else-if="currentVideo" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Back / reviewing navigation bar -->
      <div class="flex items-center justify-between mb-4">
        <button
          v-if="canGoBack"
          @click="goBack"
          class="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 transition"
        >
          <span>←</span>
          <span>Previous Video</span>
        </button>
        <span v-else></span>

        <div v-if="isReviewing" class="flex items-center gap-3">
          <span class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-amber-800 bg-amber-100 border border-amber-300 rounded-full">
            Re-labeling: {{ currentVideo.VideoID }}
          </span>
          <button
            @click="returnToCurrent"
            class="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition"
          >
            <span>Return to current video</span>
            <span>→</span>
          </button>
        </div>
      </div>

      <VideoSurvey
        :key="currentVideo.VideoID"
        :video="currentVideo"
        :narrative="currentNarrative"
        :atomic-facts="currentAtomicFacts"
        :existing-responses="existingResponses[currentVideo.VideoID]"
        :username="username"
        :is-reviewing="isReviewing"
        @submit="handleSubmit"
      />
    </div>

    <div v-else class="flex items-center justify-center min-h-[60vh]">
      <div class="text-center">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Survey Complete!</h2>
        <p class="text-gray-600 mb-6">
          You have completed all {{ totalVideos }} videos. Thank you for your participation.
        </p>
        <p class="text-sm text-gray-500 mb-4">
          Need to revisit a video? Use the dropdown above or select one below.
        </p>
        <div class="flex items-center justify-center gap-4">
          <select
            @change="goToVideo($event.target.value)"
            class="px-3 py-2 text-sm border border-gray-300 rounded-md bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="" selected disabled>Re-label a video...</option>
            <option
              v-for="v in sortedVideos"
              :key="v.VideoID"
              :value="v.VideoID"
            >
              {{ v.VideoID }}
            </option>
          </select>
          <button
            @click="handleLogout"
            class="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import VideoSurvey from './VideoSurvey.vue'
import { loadVideos, loadNarrative, loadAtomicFacts, loadUserResponses, saveUserResponse } from '../api'

const props = defineProps({
  username: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['logout'])

const loading = ref(true)
const videos = ref([])
const currentVideoIndex = ref(0)
const existingResponses = ref({})
const videoHistory = ref([])        // Ordered list of video IDs as user completes them
const reviewingVideoId = ref(null)  // Set when user is re-labeling a previous video

const isReviewing = computed(() => reviewingVideoId.value !== null)

const currentVideo = computed(() => {
  // If reviewing a previous video, show that one
  if (reviewingVideoId.value) {
    return videos.value.find(v => v.VideoID === reviewingVideoId.value) || null
  }
  if (videos.value.length === 0) return null
  const remaining = getRemainingVideos()
  return remaining.length > 0 ? remaining[0] : null
})

// Only responses explicitly submitted count as "completed"
const isVideoSubmitted = (videoId) => {
  const r = existingResponses.value[videoId]
  return r && r.submitted === true
}

const canGoBack = computed(() => {
  return Object.keys(existingResponses.value).some(id => isVideoSubmitted(id))
})

const currentNarrative = ref('')
const currentAtomicFacts = ref([])

const totalVideos = computed(() => videos.value.length)
const completedCount = computed(() => {
  return Object.keys(existingResponses.value).filter(id => isVideoSubmitted(id)).length
})
const remainingCount = computed(() => totalVideos.value - completedCount.value)
const progressPercentage = computed(() => {
  if (totalVideos.value === 0) return 0
  return (completedCount.value / totalVideos.value) * 100
})

const getRemainingVideos = () => {
  return videos.value.filter(v => !isVideoSubmitted(v.VideoID))
}

// Sorted list of all videos for the dropdown selector
const sortedVideos = computed(() => {
  return [...videos.value].sort((a, b) => a.VideoID.localeCompare(b.VideoID, undefined, { numeric: true }))
})

// The VideoID that is currently active (reviewing or natural next)
const activeVideoId = computed(() => currentVideo.value?.VideoID || null)

const goToVideo = (videoId) => {
  if (!videoId) return
  // If this is the natural next uncompleted video, clear review mode
  const remaining = getRemainingVideos()
  const nextNatural = remaining.length > 0 ? remaining[0].VideoID : null
  if (videoId === nextNatural) {
    reviewingVideoId.value = null
  } else {
    reviewingVideoId.value = videoId
  }
}

const shuffleArray = (array) => {
  const shuffled = [...array]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

const loadCurrentVideoData = async () => {
  if (!currentVideo.value) return
  
  try {
    const videoId = currentVideo.value.VideoID
    const narrativeId = currentVideo.value['Police Report ID']
    
    const [narrative, facts] = await Promise.all([
      loadNarrative(narrativeId),
      loadAtomicFacts(videoId)
    ])
    
    currentNarrative.value = narrative
    currentAtomicFacts.value = facts
  } catch (error) {
    console.error('Error loading video data:', error)
  }
}

// Build ordered list: session history first, then any other submitted videos sorted by ID
const completedVideoList = computed(() => {
  const historySet = new Set(videoHistory.value)
  const otherCompleted = Object.keys(existingResponses.value)
    .filter(id => isVideoSubmitted(id) && !historySet.has(id))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  // Session history (oldest→newest), then previously completed (sorted)
  return [...videoHistory.value, ...otherCompleted]
})

const goBack = () => {
  const list = completedVideoList.value
  if (list.length === 0) return

  if (isReviewing.value) {
    // Move one step earlier in the completed list
    const idx = list.indexOf(reviewingVideoId.value)
    if (idx > 0) {
      reviewingVideoId.value = list[idx - 1]
    }
  } else {
    // Jump to the most recent item (last in session history, or last completed)
    reviewingVideoId.value = list[list.length - 1]
  }
}

const returnToCurrent = () => {
  reviewingVideoId.value = null
}

const handleSubmit = async (responses) => {
  const videoId = currentVideo.value.VideoID
  try {
    const submittedResponses = { ...responses, submitted: true }
    await saveUserResponse(props.username, videoId, submittedResponses)
    existingResponses.value[videoId] = submittedResponses

    if (isReviewing.value) {
      // Done re-labeling — return to the next uncompleted video
      reviewingVideoId.value = null
    } else {
      // Normal flow — record in history
      videoHistory.value.push(videoId)
    }

    // Wait a moment for the computed property to update, then load next video
    await new Promise(resolve => setTimeout(resolve, 100))
    await loadCurrentVideoData()
  } catch (error) {
    console.error('Error saving response:', error)
    alert('Error saving response. Please try again.')
  }
}

const handleLogout = () => {
  emit('logout')
}

// Watch for video changes and load data
watch(currentVideo, async (newVideo) => {
  if (newVideo) {
    await loadCurrentVideoData()
  }
}, { immediate: false })

onMounted(async () => {
  try {
    const allVideos = await loadVideos()
    const userResponses = await loadUserResponses(props.username)
    
    existingResponses.value = userResponses
    
    // Shuffle videos for randomization
    videos.value = shuffleArray(allVideos)
    
    // Load first video data
    await loadCurrentVideoData()
    
    loading.value = false
  } catch (error) {
    console.error('Error initializing survey:', error)
    loading.value = false
  }
})
</script>
