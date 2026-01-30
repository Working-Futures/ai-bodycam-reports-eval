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
          <div class="text-right">
            <p class="text-sm font-medium text-gray-700">
              Progress: {{ completedCount }} / {{ totalVideos }} videos completed
            </p>
            <p class="text-xs text-gray-500">
              {{ remainingCount }} remaining
            </p>
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
      <VideoSurvey
        :key="currentVideo.VideoID"
        :video="currentVideo"
        :narrative="currentNarrative"
        :atomic-facts="currentAtomicFacts"
        :existing-responses="existingResponses[currentVideo.VideoID]"
        :username="username"
        @submit="handleSubmit"
      />
    </div>

    <div v-else class="flex items-center justify-center min-h-[60vh]">
      <div class="text-center">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Survey Complete!</h2>
        <p class="text-gray-600 mb-6">
          You have completed all {{ totalVideos }} videos. Thank you for your participation.
        </p>
        <button
          @click="handleLogout"
          class="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Logout
        </button>
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

const currentVideo = computed(() => {
  if (videos.value.length === 0) return null
  const remaining = getRemainingVideos()
  return remaining.length > 0 ? remaining[0] : null
})

const currentNarrative = ref('')
const currentAtomicFacts = ref([])

const totalVideos = computed(() => videos.value.length)
const completedCount = computed(() => {
  return Object.keys(existingResponses.value).length
})
const remainingCount = computed(() => totalVideos.value - completedCount.value)
const progressPercentage = computed(() => {
  if (totalVideos.value === 0) return 0
  return (completedCount.value / totalVideos.value) * 100
})

const getRemainingVideos = () => {
  const completedIds = new Set(Object.keys(existingResponses.value))
  return videos.value.filter(v => !completedIds.has(v.VideoID))
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

const handleSubmit = async (responses) => {
  const videoId = currentVideo.value.VideoID
  try {
    await saveUserResponse(props.username, videoId, responses)
    existingResponses.value[videoId] = responses
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
