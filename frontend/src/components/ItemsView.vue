<template>
  <div id="items-section">
    <div class="list-header">
      <button class="back-button" @click="$emit('back')">
        <img src="/images/left.png" alt="Back" class="back-icon" />
      </button>
      <h2>{{ listName }}</h2>
      <button id="share-list-button" @click="shareList">Share List</button>
    </div>

    <KinopoiskSearch :listId="listId" @added="fetchItems" />

    <div id="items-container">
      <div
        v-for="item in items"
        :key="item.id"
        class="item"
        :class="{ watched: item.watched }"
      >
        <img :src="item.cover_url || 'placeholder.jpg'" :alt="item.title" />
        <div class="item-content">
          <strong>{{ item.title }} ({{ item.type }})</strong>
          <div v-if="item.genre">Жанр: {{ item.genre }}</div>
          <div class="full-description" v-if="expandedItemId === item.id">
            {{ item.description || 'Нет описания' }}
          </div>
          <div class="item-buttons">
            <button @click="toggleDescription(item)">
              {{ expandedItemId === item.id ? 'Скрыть' : 'Подробнее' }}
            </button>
            <button @click="toggleWatched(item)">
              {{ item.watched ? 'Unwatch' : 'Watched' }}
            </button>
            <button @click="deleteItem(item)">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import KinopoiskSearch from './KinopoiskSearch.vue'

const props = defineProps({
  listId: Number,
  listName: String
})

const items = ref([])
const expandedItemId = ref(null)

async function fetchItems() {
  const res = await api.get('/items', { params: { list_id: props.listId } })
  items.value = res.data
}

async function toggleWatched(item) {
  await api.patch('/items', { id: item.id, watched: !item.watched })
  fetchItems()
}

async function deleteItem(item) {
  if (!confirm('Delete this item?')) return
  await api.delete('/items', { data: { id: item.id } })
  fetchItems()
}

async function shareList() {
  const username = prompt('Enter username to share with:')
  if (!username) return
  await api.post('/share', { list_id: props.listId, username })
  alert(`List shared with ${username}!`)
}

async function toggleDescription(item) {
  if (expandedItemId.value === item.id) {
    expandedItemId.value = null
    return
  }
  expandedItemId.value = item.id
  // загрузка описания из Кинопоиска
  const res = await fetch(`https://api.kinopoisk.dev/v1.4/movie/search?query=${encodeURIComponent(item.title)}`, {
    headers: { 'X-API-KEY': import.meta.env.VITE_KINOPOISK_KEY }
  })
  const data = await res.json()
  if (data.docs?.length > 0) {
    item.description = data.docs[0].description || ''
  }
}

onMounted(fetchItems)
</script>
