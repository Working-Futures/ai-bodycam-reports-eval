<template>
  <div class="min-h-screen bg-gray-50">
    <UsernameEntry v-if="!username" @username-set="handleUsernameSet" />
    <SurveyPage 
      v-else 
      :username="username"
      @logout="handleLogout"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UsernameEntry from './components/UsernameEntry.vue'
import SurveyPage from './components/SurveyPage.vue'

const username = ref(localStorage.getItem('username') || '')

const handleUsernameSet = (newUsername) => {
  username.value = newUsername
  localStorage.setItem('username', newUsername)
}

const handleLogout = () => {
  username.value = ''
  localStorage.removeItem('username')
}
</script>
