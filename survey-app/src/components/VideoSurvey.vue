<template>
  <div class="space-y-6">
    <!-- Welcome Section -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-4">Welcome</h2>
      <p class="text-gray-700 leading-relaxed">
        You will watch a short body-worn camera video from a police officer's perspective. 
        Please watch the video in its entirety before answering the questions that follow. 
        There are no right or wrong answers—we are interested in your honest assessment 
        based only on what is shown in the video.
      </p>
    </div>

    <!-- Video Embed -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-3">Video</h3>
      <div class="max-w-2xl mx-auto">
        <div class="aspect-video bg-black rounded-lg overflow-hidden" style="max-height: 300px;">
          <iframe
            :src="embedUrl"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
            class="w-full h-full"
          ></iframe>
        </div>
      </div>
    </div>

    <!-- Narrative Section -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-xl font-semibold text-gray-900 mb-4">
        Please answer these questions after watching the video in its entirety based on your understanding of the provided police report:
      </h3>
      <div class="max-h-96 overflow-y-auto border border-gray-200 rounded-md p-4 bg-gray-50">
        <pre class="whitespace-pre-wrap text-sm text-gray-700 font-sans">{{ narrative }}</pre>
      </div>
    </div>

    <!-- Likert Scale Questions Section -->
    <div v-if="!showAtomicFacts" class="bg-white rounded-lg shadow p-6">
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-xl font-semibold text-gray-900">
          Questions ({{ currentLikertIndex + 1 }} of {{ likertQuestions.length }})
        </h3>
        <div class="flex gap-2 items-center">
          <button
            v-if="currentLikertIndex > 0"
            @click="goToPreviousLikert"
            class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition"
          >
            ← Previous
          </button>
          <button
            v-if="currentLikertIndex < likertQuestions.length - 1"
            @click="goToNextLikert"
            :disabled="!currentLikertAnswer"
            class="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
          >
            Next →
          </button>
          <button
            v-else-if="allLikertAnswered"
            @click="showAtomicFacts = true"
            class="px-4 py-2 text-sm text-white bg-green-600 rounded-md hover:bg-green-700 transition"
          >
            Continue to Atomic Facts →
          </button>
          <label v-if="currentLikertIndex < likertQuestions.length - 1" class="flex items-center gap-2 ml-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              v-model="autoAdvanceLikert"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span>Auto-advance</span>
          </label>
        </div>
      </div>

      <!-- Current Question -->
      <Transition name="fade-in" mode="out-in">
        <div 
          ref="likertQuestionRef" 
          :key="`likert-${currentLikertIndex}`"
          class="border-2 border-blue-200 rounded-lg p-6 bg-blue-50 mb-6"
        >
          <LikertQuestion
            :question="likertQuestions[currentLikertIndex]"
            :value="currentLikertAnswer"
            @update="(value) => updateLikertResponse(currentLikertIndex, value)"
          />
        </div>
      </Transition>

      <!-- Answered Questions (Collapsed) -->
      <div v-if="answeredLikertQuestions.length > 0" class="space-y-2">
        <div
          v-for="(answered, idx) in answeredLikertQuestions"
          :key="answered.index"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-gray-200 cursor-pointer hover:bg-gray-100 transition"
          @click="goToLikertQuestion(answered.index)"
        >
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-700 line-clamp-1">
              {{ answered.question }}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Answer: {{ getAnswerLabel(answered.answer) }}
            </p>
          </div>
          <button
            class="ml-4 px-3 py-1 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition"
            @click.stop="goToLikertQuestion(answered.index)"
          >
            Edit
          </button>
        </div>
      </div>
    </div>

    <!-- Atomic Facts Section -->
    <div v-else class="bg-white rounded-lg shadow p-6">
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-xl font-semibold text-gray-900">
          Atomic Facts ({{ currentAtomicIndex + 1 }} of {{ atomicFacts.length }})
        </h3>
        <div class="flex gap-2 items-center">
          <button
            @click="showAtomicFacts = false"
            class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition"
          >
            ← Back to Questions
          </button>
          <button
            v-if="currentAtomicIndex > 0"
            @click="goToPreviousAtomic"
            class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition"
          >
            ← Previous
          </button>
          <button
            v-if="currentAtomicIndex < atomicFacts.length - 1"
            @click="goToNextAtomic"
            :disabled="!currentAtomicAnswer"
            class="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
          >
            Next →
          </button>
          <label v-if="currentAtomicIndex < atomicFacts.length - 1" class="flex items-center gap-2 ml-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              v-model="autoAdvanceAtomic"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span>Auto-advance</span>
          </label>
        </div>
      </div>

      <div class="mb-6 p-4 bg-gray-50 rounded-md border border-gray-200">
            <!-- Submit Button (only show when all atomic facts are answered) -->
    <div v-if="showAtomicFacts && allAtomicFactsAnswered" class="flex justify-end pb-8">
      <button
        @click="handleSubmit"
        class="px-8 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition font-medium"
      >
        Submit and Continue
      </button>
    </div>
        <h4 class="text-sm font-semibold text-gray-900 mb-2">Instructions:</h4>
        <div class="prose prose-sm max-w-none text-gray-700">
          <p class="mb-2">
            You will be shown a set of atomic fact statements derived from a police report. 
            For each atomic fact, indicate whether it is:
          </p>
          <ul class="list-disc pl-5 space-y-1 mb-2">
            <li>
              <strong>Accurate:</strong> The statement in its entirety is explicitly supported by the video you just watched.
            </li>
            <li>
              <strong>Inaccurate:</strong> The statement contradicts the video, or the statement describes something that is clearly shown differently in the video.
            </li>
            <li>
              <strong>Unsupported:</strong> The statement cannot be verified from the video. The video does not provide enough information to confirm or deny the statement.
            </li>
          </ul>
          <p class="text-xs italic">
            Important guidelines: Base your judgments only on what is visible or audible in the video. 
            Do not make assumptions or inferences beyond the video. If the video does not clearly show or state the fact, 
            select Unsupported. If placeholders appear in the statement (e.g., [INSERT: name]), treat them as written.
          </p>
        </div>
      </div>

      <!-- Current Atomic Fact -->
      <Transition name="fade-in" mode="out-in">
        <div 
          ref="atomicQuestionRef" 
          :key="`atomic-${currentAtomicIndex}`"
          class="border-2 border-blue-200 rounded-lg p-6 bg-blue-50 mb-6"
        >
          <AtomicFactQuestion
            :fact="atomicFacts[currentAtomicIndex]"
            :index="currentAtomicIndex + 1"
            :value="currentAtomicAnswer"
            @update="(value) => updateAtomicFactResponse(currentAtomicIndex, value)"
          />
        </div>
      </Transition>

      <!-- Answered Atomic Facts (Collapsed) -->
      <div v-if="answeredAtomicFacts.length > 0" class="space-y-2">
        <div
          v-for="(answered, idx) in answeredAtomicFacts"
          :key="answered.index"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-gray-200 cursor-pointer hover:bg-gray-100 transition"
          @click="goToAtomicQuestion(answered.index)"
        >
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-700 line-clamp-2">
              {{ answered.fact }}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Answer: {{ getAtomicAnswerLabel(answered.answer) }}
            </p>
          </div>
          <button
            class="ml-4 px-3 py-1 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition"
            @click.stop="goToAtomicQuestion(answered.index)"
          >
            Edit
          </button>
        </div>
      </div>
    </div>



    <!-- Fixed compact question when scrolled out of view (Likert) -->
    <Transition name="slide-up">
      <div
        v-if="!showAtomicFacts && !isLikertQuestionVisible"
        :key="`fixed-likert-${currentLikertIndex}`"
        class="fixed bottom-0 left-0 right-0 z-50 bg-blue-50 border-t-2 border-blue-200 shadow-lg"
      >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between gap-4">
          <p class="text-sm font-medium text-gray-700 flex-1 line-clamp-3 leading-relaxed">
            {{ likertQuestions[currentLikertIndex] }}
          </p>
          <div class="flex gap-2 flex-shrink-0">
            <button
              v-for="(option, index) in likertOptions"
              :key="option.value"
              @click="updateLikertResponse(currentLikertIndex, option.value)"
              :class="[
                'px-3 py-2.5 text-xs rounded-md border-2 transition relative',
                currentLikertAnswer === option.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
              ]"
            >
              <span class="absolute top-0.5 left-0.5 w-3 h-3 border border-red-300 text-red-500 text-[10px] rounded flex items-center justify-center font-mono font-semibold bg-transparent shadow-sm">
                {{ index + 1 }}
              </span>
              {{ option.shortLabel }}
            </button>
          </div>
        </div>
      </div>
      </div>
    </Transition>

    <!-- Fixed compact question when scrolled out of view (Atomic) -->
    <Transition name="slide-up">
      <div
        v-if="showAtomicFacts && !isAtomicQuestionVisible"
        :key="`fixed-atomic-${currentAtomicIndex}`"
        class="fixed bottom-0 left-0 right-0 z-50 bg-blue-50 border-t-2 border-blue-200 shadow-lg"
      >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between gap-4">
          <p class="text-sm font-medium text-gray-700 flex-1 line-clamp-3 leading-relaxed">
            {{ atomicFacts[currentAtomicIndex] }}
          </p>
          <div class="flex gap-2 flex-shrink-0">
            <button
              v-for="(option, index) in atomicOptions"
              :key="option.value"
              @click="updateAtomicFactResponse(currentAtomicIndex, option.value)"
              :class="[
                'px-3 py-2.5 text-xs rounded-md border-2 transition font-medium relative',
                currentAtomicAnswer === option.value
                  ? getActiveClass(option.value)
                  : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
              ]"
            >
              <span class="absolute top-0.5 left-0.5 w-3 h-3 border border-red-300 text-red-500 text-[10px] rounded flex items-center justify-center font-mono font-semibold bg-transparent shadow-sm">
                {{ index + 1 }}
              </span>
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import LikertQuestion from './LikertQuestion.vue'
import AtomicFactQuestion from './AtomicFactQuestion.vue'
import { saveUserResponse } from '../api'

const likertQuestionRef = ref(null)
const atomicQuestionRef = ref(null)
const isLikertQuestionVisible = ref(true)
const isAtomicQuestionVisible = ref(true)

const likertOptions = [
  { value: 'strongly_disagree', label: 'Strongly Disagree', shortLabel: 'Str. Disagree' },
  { value: 'disagree', label: 'Disagree', shortLabel: 'Disagree' },
  { value: 'agree', label: 'Agree', shortLabel: 'Agree' },
  { value: 'strongly_agree', label: 'Strongly Agree', shortLabel: 'Str. Agree' }
]

const atomicOptions = [
  { value: 'accurate', label: 'Accurate' },
  { value: 'inaccurate', label: 'Inaccurate' },
  { value: 'unsupported', label: 'Unsupported' }
]

const getActiveClass = (value) => {
  const classes = {
    accurate: 'bg-green-600 text-white border-green-600',
    inaccurate: 'bg-red-600 text-white border-red-600',
    unsupported: 'bg-yellow-500 text-white border-yellow-500'
  }
  return classes[value] || 'bg-blue-600 text-white border-blue-600'
}

const props = defineProps({
  video: {
    type: Object,
    required: true
  },
  narrative: {
    type: String,
    required: true
  },
  atomicFacts: {
    type: Array,
    required: true
  },
  existingResponses: {
    type: Object,
    default: null
  },
  username: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['submit'])

const likertQuestions = [
  'Are all key individuals (suspect, victim, witness, officer) clearly and correctly defined and described within the report?',
  'Does the report correctly describe what each party did, in sequence?',
  'Does the report correctly explain why or how the incident occurred?',
  'Does the report correctly mention if the officer provided Miranda or other legal warnings?',
  'Does the report correctly note whether the individual complied, resisted or fled?',
  'Does the report correctly describe any searches or investigative actions taken?',
  'Does the report correctly contain whether the officer stated the basis for probable cause or citation/arrest decision?',
  'Does the report correctly document any use of force?'
]

const responses = ref({
  likertQuestions: [],
  atomicFacts: []
})

const currentLikertIndex = ref(0)
const currentAtomicIndex = ref(0)
const showAtomicFacts = ref(false)
const autoAdvanceLikert = ref(false)
const autoAdvanceAtomic = ref(false)

// Auto-save functionality
let saveTimeout = null
const isSaving = ref(false)

const autoSave = async () => {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }
  
  saveTimeout = setTimeout(async () => {
    try {
      isSaving.value = true
      const videoId = props.video.VideoID
      await saveUserResponse(props.username, videoId, responses.value)
    } catch (error) {
      console.error('Error auto-saving response:', error)
      // Don't show alert for auto-save failures to avoid interrupting user
    } finally {
      isSaving.value = false
    }
  }, 1000) // Debounce: save 1 second after last change
}

// Watch for response changes and auto-save
watch(() => responses.value, () => {
  autoSave()
}, { deep: true })

// Cleanup timeout on unmount
onUnmounted(() => {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }
})

// Load existing responses if available
watch(() => props.existingResponses, (newVal) => {
  if (newVal) {
    responses.value = {
      likertQuestions: newVal.likertQuestions || [],
      atomicFacts: newVal.atomicFacts || []
    }
    // If all likert questions are answered, show atomic facts
    if (responses.value.likertQuestions && responses.value.likertQuestions.every(q => q !== null && q !== undefined)) {
      showAtomicFacts.value = true
    }
  } else {
    responses.value = {
      likertQuestions: new Array(likertQuestions.length).fill(null),
      atomicFacts: new Array(props.atomicFacts.length).fill(null)
    }
  }
}, { immediate: true })

// Initialize responses when component mounts or data changes
watch([() => props.atomicFacts], () => {
  if (!props.existingResponses) {
    responses.value.atomicFacts = new Array(props.atomicFacts.length).fill(null)
  }
}, { immediate: true })

const embedUrl = computed(() => {
  const url = props.video['Video Link']
  if (!url) return ''
  
  // Convert YouTube URL to embed format
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  if (match) {
    return `https://www.youtube.com/embed/${match[1]}`
  }
  return url
})

const currentLikertAnswer = computed(() => {
  const response = responses.value.likertQuestions?.[currentLikertIndex.value]
  if (!response) return null
  return response.value
})

const currentAtomicAnswer = computed(() => {
  const response = responses.value.atomicFacts?.[currentAtomicIndex.value]
  if (!response) return null
  return response.value
})

const allLikertAnswered = computed(() => {
  return responses.value.likertQuestions?.every(q => {
    if (!q) return false
    return (typeof q === 'object' && q.value !== undefined) || q !== null
  })
})

const allAtomicFactsAnswered = computed(() => {
  return responses.value.atomicFacts?.every(f => {
    if (!f) return false
    return (typeof f === 'object' && f.value !== undefined) || f !== null
  })
})

const answeredLikertQuestions = computed(() => {
  return likertQuestions
    .map((q, idx) => ({
      question: q,
      index: idx,
      answer: responses.value.likertQuestions?.[idx]?.value
    }))
    .filter(item => item.answer !== null && item.answer !== undefined && item.index !== currentLikertIndex.value)
    .sort((a, b) => a.index - b.index)
})

const answeredAtomicFacts = computed(() => {
  return props.atomicFacts
    .map((fact, idx) => ({
      fact,
      index: idx,
      answer: responses.value.atomicFacts?.[idx]?.value
    }))
    .filter(item => item.answer !== null && item.answer !== undefined && item.index !== currentAtomicIndex.value)
    .sort((a, b) => a.index - b.index)
})

const updateLikertResponse = (index, value) => {
  if (!responses.value.likertQuestions) {
    responses.value.likertQuestions = new Array(likertQuestions.length).fill(null)
  }
  responses.value.likertQuestions[index] = {
    id: index,
    question: likertQuestions[index],
    value: value
  }
  
  // Auto-advance if enabled and not on last question
  if (autoAdvanceLikert.value && index < likertQuestions.length - 1) {
    setTimeout(() => {
      if (currentLikertIndex.value === index) {
        goToNextLikert()
      }
    }, 300)
  }
}

const updateAtomicFactResponse = (index, value) => {
  if (!responses.value.atomicFacts) {
    responses.value.atomicFacts = new Array(props.atomicFacts.length).fill(null)
  }
  responses.value.atomicFacts[index] = {
    id: index,
    fact: props.atomicFacts[index],
    value: value
  }
  
  // Auto-advance if enabled and not on last question
  if (autoAdvanceAtomic.value && index < props.atomicFacts.length - 1) {
    setTimeout(() => {
      if (currentAtomicIndex.value === index) {
        goToNextAtomic()
      }
    }, 300)
  }
}

const goToNextLikert = () => {
  if (currentLikertIndex.value < likertQuestions.length - 1) {
    currentLikertIndex.value++
  }
}

const goToPreviousLikert = () => {
  if (currentLikertIndex.value > 0) {
    currentLikertIndex.value--
  }
}

const goToLikertQuestion = (index) => {
  currentLikertIndex.value = index
}

const goToNextAtomic = () => {
  if (currentAtomicIndex.value < props.atomicFacts.length - 1) {
    currentAtomicIndex.value++
  }
}

const goToPreviousAtomic = () => {
  if (currentAtomicIndex.value > 0) {
    currentAtomicIndex.value--
  }
}

const goToAtomicQuestion = (index) => {
  currentAtomicIndex.value = index
}

const getAnswerLabel = (value) => {
  const labels = {
    'strongly_disagree': 'Strongly Disagree',
    'disagree': 'Disagree',
    'agree': 'Agree',
    'strongly_agree': 'Strongly Agree'
  }
  return labels[value] || value
}

const getAtomicAnswerLabel = (value) => {
  const labels = {
    'accurate': 'Accurate',
    'inaccurate': 'Inaccurate',
    'unsupported': 'Unsupported'
  }
  return labels[value] || value
}

const handleSubmit = () => {
  if (allLikertAnswered.value && allAtomicFactsAnswered.value) {
    emit('submit', responses.value)
  }
}

// Keyboard shortcuts
const handleKeyPress = (event) => {
  // Only handle if not typing in an input field
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
    return
  }

  const key = event.key
  
  // Handle Likert questions (1-4)
  if (!showAtomicFacts.value && key >= '1' && key <= '4') {
    const likertOptions = [
      'strongly_disagree',
      'disagree',
      'agree',
      'strongly_agree'
    ]
    const optionIndex = parseInt(key) - 1
    if (optionIndex >= 0 && optionIndex < likertOptions.length) {
      updateLikertResponse(currentLikertIndex.value, likertOptions[optionIndex])
    }
  }
  
  // Handle Atomic Facts (1-3)
  if (showAtomicFacts.value && key >= '1' && key <= '3') {
    const atomicOptions = [
      'accurate',
      'inaccurate',
      'unsupported'
    ]
    const optionIndex = parseInt(key) - 1
    if (optionIndex >= 0 && optionIndex < atomicOptions.length) {
      updateAtomicFactResponse(currentAtomicIndex.value, atomicOptions[optionIndex])
    }
  }
}

// Intersection Observer for visibility detection
let likertObserver = null
let atomicObserver = null

onMounted(() => {
  window.addEventListener('keydown', handleKeyPress)

  // Set up intersection observer for Likert questions
  if (likertQuestionRef.value) {
    likertObserver = new IntersectionObserver(
      (entries) => {
        isLikertQuestionVisible.value = entries[0].isIntersecting
      },
      { threshold: 0.5 }
    )
    likertObserver.observe(likertQuestionRef.value)
  }

  // Set up intersection observer for Atomic facts
  // Use nextTick to ensure element is rendered
  setTimeout(() => {
    if (atomicQuestionRef.value) {
      atomicObserver = new IntersectionObserver(
        (entries) => {
          isAtomicQuestionVisible.value = entries[0].isIntersecting
        },
        { threshold: 0.5 }
      )
      atomicObserver.observe(atomicQuestionRef.value)
    }
  }, 100)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
  if (likertObserver) {
    likertObserver.disconnect()
  }
  if (atomicObserver) {
    atomicObserver.disconnect()
  }
})

// Watch for question changes to update observers
watch([currentLikertIndex, showAtomicFacts, currentAtomicIndex], () => {
  setTimeout(() => {
    if (likertObserver && likertQuestionRef.value && !showAtomicFacts.value) {
      likertObserver.disconnect()
      likertObserver.observe(likertQuestionRef.value)
      isLikertQuestionVisible.value = true
    }
    if (showAtomicFacts.value) {
      // Re-initialize atomic observer when switching to atomic facts
      if (atomicObserver && atomicQuestionRef.value) {
        atomicObserver.disconnect()
        atomicObserver.observe(atomicQuestionRef.value)
        isAtomicQuestionVisible.value = true
      } else if (atomicQuestionRef.value) {
        // Create observer if it doesn't exist yet
        atomicObserver = new IntersectionObserver(
          (entries) => {
            isAtomicQuestionVisible.value = entries[0].isIntersecting
          },
          { threshold: 0.5 }
        )
        atomicObserver.observe(atomicQuestionRef.value)
        isAtomicQuestionVisible.value = true
      }
    }
  }, 150)
})
</script>
