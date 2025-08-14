<template>
  <div id="auth-section">
    <h2>Login / Register</h2>
    <form @submit.prevent="submit">
      <input v-model="username" placeholder="Username" required />
      <input type="password" v-model="password" placeholder="Password" required />
      <button>Login / Register</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api'
const emit = defineEmits(['login'])

const username = ref('')
const password = ref('')

async function submit() {
  try {
    const userCheck = await api.get(`/user`, { params: { username: username.value } })
    if (userCheck.status === 200) {
        console.log("here")
      const res = await api.post(`/login`, { username: username.value, password: password.value })
      console.log("here2")
      localStorage.setItem('token', res.data.token)
      console.log("here3")
      localStorage.setItem('user_id', res.data.user_id)
      console.log("here4")
      emit('login')
    }
  } catch {
    
        console.log("here1")
    const res = await api.post(`/register`, { username: username.value, password: password.value })
    localStorage.setItem('token', res.data.token)
    localStorage.setItem('user_id', res.data.user_id)
    emit('login')
  }
}
</script>
