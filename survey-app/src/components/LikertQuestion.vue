<template>
  <div>
    <label class="block text-lg font-semibold text-gray-900 mb-6">
      {{ question }}
    </label>
    <div class="flex items-center justify-center gap-2">
      <button
        v-for="(option, index) in options"
        :key="option.value"
        @click="$emit('update', option.value)"
        :class="[
          'flex-1 px-2 py-2 rounded-md border-2 transition relative min-w-0 text-sm h-14',
          value === option.value
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
        ]"
      >
        <span class="absolute top-1 left-1 w-4 h-4 border border-gray-400 text-gray-600 text-[10px] rounded flex items-center justify-center font-mono font-semibold bg-transparent z-10">
          {{ index + 1 }}
        </span>
        <span class="relative z-0 block text-center leading-tight">{{ option.label }}</span>
      </button>
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
