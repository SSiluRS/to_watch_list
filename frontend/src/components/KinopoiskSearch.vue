<template>
  <div>
    <input v-model="query" placeholder="Найти фильм..." />
    <button @click="search">Поиск</button>
    <ul id="kinopoisk-results">
      <li v-for="doc in results" :key="doc.id">
        <div class="item">
          <img :src="doc.poster?.previewUrl || ''" alt="poster" />
          <div class="item-content">
            <strong>{{ doc.name }}</strong>
            <span>{{ doc.year || '' }} {{ doc.genres.map(g => g.name).join(', ') }}</span>
            <p>{{ doc.shortDescription || '' }}</p>
            <button @click="addFromKinopoisk(doc)">Добавить</button>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api'

const props = defineProps({
  listId: Number
})

const emit = defineEmits(['added'])
const query = ref('')
const results = ref([])

async function search() {
  if (!query.value.trim()) return;
  
  try {
    const res = await api.get(`/kinopoisk/search`, {
      params: { query: query.value.trim() }
    });
    results.value = res.data.docs || [];
  } catch (err) {
    console.error('Kinopoisk API error', err);
  }
}


async function addFromKinopoisk(doc) {
  await api.post('/items', {
    list_id: props.listId,
    title: doc.name,
    type: doc.type || 'movie',
    genre: doc.genres.map(g => g.name).join(', '),
    cover_url: doc.poster?.url || ''
  })
  emit('added')
  query.value = ''
  results.value = []
}
</script>
