<template>
  <div class="border border-gray-200 rounded-lg p-4 bg-gray-50">
    <div class="flex items-start space-x-4">
      <div class="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center font-semibold text-sm">
        {{ index }}
      </div>
      <div class="flex-1">
        <p class="text-gray-800 mb-4">{{ fact }}</p>
        <div class="flex space-x-3">
          <button
            v-for="(option, index) in options"
            :key="option.value"
            @click="$emit('update', option.value)"
            :class="[
              'px-4 py-3 rounded-md border-2 transition font-medium relative',
              value === option.value
                ? getActiveClass(option.value)
                : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
            ]"
          >
            <span class="absolute top-1 left-1 w-4 h-4 border border-red-300 text-red-500 text-[10px] rounded flex items-center justify-center font-mono font-semibold bg-transparent z-10 shadow-sm">
              {{ index + 1 }}
            </span>
            <span class="relative z-0">{{ option.label }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  fact: {
    type: String,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  value: {
    type: String,
    default: null
  }
})

defineEmits(['update'])

const options = [
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
</script>
