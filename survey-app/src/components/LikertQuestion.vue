<template>
  <div>
    <label class="block text-lg font-semibold text-gray-900 mb-6">
      {{ question }}
    </label>
    <div class="flex items-center justify-between space-x-4">
      <span class="text-xs text-gray-500 w-24">Strongly Disagree</span>
      <div class="flex-1 flex items-center justify-center space-x-2">
        <button
          v-for="option in options"
          :key="option.value"
          @click="$emit('update', option.value)"
          :class="[
            'px-4 py-2 rounded-md border-2 transition',
            value === option.value
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
          ]"
        >
          {{ option.label }}
        </button>
      </div>
      <span class="text-xs text-gray-500 w-24 text-right">Strongly Agree</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  question: {
    type: String,
    required: true
  },
  value: {
    type: String,
    default: null
  }
})

defineEmits(['update'])

const options = [
  { value: 'strongly_disagree', label: 'Strongly Disagree' },
  { value: 'disagree', label: 'Disagree' },
  { value: 'agree', label: 'Agree' },
  { value: 'strongly_agree', label: 'Strongly Agree' }
]
</script>
