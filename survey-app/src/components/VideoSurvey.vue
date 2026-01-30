<template>
  <div class="space-y-8">
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
      <h3 class="text-xl font-semibold text-gray-900 mb-4">Video</h3>
      <div class="aspect-video bg-black rounded-lg overflow-hidden">
        <iframe
          :src="embedUrl"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen
          class="w-full h-full"
        ></iframe>
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

    <!-- Likert Scale Questions -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-xl font-semibold text-gray-900 mb-6">Questions</h3>
      <div class="space-y-6">
        <LikertQuestion
          v-for="(question, index) in likertQuestions"
          :key="index"
          :question="question"
          :value="responses.likertQuestions?.[index]"
          @update="(value) => updateLikertResponse(index, value)"
        />
      </div>
    </div>

    <!-- Atomic Facts Section -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-xl font-semibold text-gray-900 mb-4">
        Please read carefully before answering the questions below.
      </h3>
      <div class="prose max-w-none mb-6 text-gray-700">
        <p class="mb-4">
          You will be shown a set of atomic fact statements derived from a police report. 
          For each atomic fact, indicate whether it is:
        </p>
        <ul class="list-disc pl-6 space-y-2 mb-4">
          <li>
            <strong>Accurate:</strong> The statement in its entirety is explicitly supported by the video you just watched. 
            The fact appears clearly and unambiguously in the video.
          </li>
          <li>
            <strong>Inaccurate:</strong> The statement contradicts the video, or the statement describes something that is clearly shown differently in the video.
          </li>
          <li>
            <strong>Unsupported:</strong> The statement cannot be verified from the video. The video does not provide enough information to confirm or deny the statement.
          </li>
        </ul>
        <p class="text-sm italic">
          Important guidelines: Base your judgments only on what is visible or audible in the video. 
          Do not make assumptions or inferences beyond the video. If the video does not clearly show or state the fact, 
          select Unsupported. If placeholders appear in the statement (e.g., [INSERT: name]), treat them as written. 
          Please use your best judgment and answer as accurately as possible. If you do not remember the relevant details, 
          please watch the video while you are responding.
        </p>
      </div>

      <div class="space-y-6 mt-8">
        <AtomicFactQuestion
          v-for="(fact, index) in atomicFacts"
          :key="index"
          :fact="fact"
          :index="index + 1"
          :value="responses.atomicFacts?.[index]"
          @update="(value) => updateAtomicFactResponse(index, value)"
        />
      </div>
    </div>

    <!-- Submit Button -->
    <div class="flex justify-end pb-8">
      <button
        @click="handleSubmit"
        :disabled="!isFormComplete"
        class="px-8 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition font-medium"
      >
        Submit and Continue
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import LikertQuestion from './LikertQuestion.vue'
import AtomicFactQuestion from './AtomicFactQuestion.vue'

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

// Load existing responses if available
watch(() => props.existingResponses, (newVal) => {
  if (newVal) {
    responses.value = {
      likertQuestions: newVal.likertQuestions || [],
      atomicFacts: newVal.atomicFacts || []
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

const updateLikertResponse = (index, value) => {
  if (!responses.value.likertQuestions) {
    responses.value.likertQuestions = new Array(likertQuestions.length).fill(null)
  }
  responses.value.likertQuestions[index] = value
}

const updateAtomicFactResponse = (index, value) => {
  if (!responses.value.atomicFacts) {
    responses.value.atomicFacts = new Array(props.atomicFacts.length).fill(null)
  }
  responses.value.atomicFacts[index] = value
}

const isFormComplete = computed(() => {
  const allLikertAnswered = responses.value.likertQuestions?.every(q => q !== null && q !== undefined)
  const allAtomicFactsAnswered = responses.value.atomicFacts?.every(f => f !== null && f !== undefined)
  return allLikertAnswered && allAtomicFactsAnswered
})

const handleSubmit = () => {
  if (isFormComplete.value) {
    emit('submit', responses.value)
  }
}
</script>
