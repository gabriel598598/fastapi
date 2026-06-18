este proyecto es un Desarrollo de una API REST con FastAPI, SQLAlchemy y Pydantic, implementando CRUD completo, 
validación de datos, manejo de relaciones entre tablas y documentación automática mediante Swagger/OpenAPI.

------Enpoints --------

GET /posts
Obtiene todos los posts con paginación, búsqueda y ordenamiento.

GET /posts/{post_id}
Obtiene un post específico por ID.

POST /posts
Crea un nuevo post con autor y etiquetas.

PUT /posts/{post_id}
Actualiza un post existente.

DELETE /posts/{post_id}
Elimina un post.

GET /posts/by-tags
Filtra posts por etiquetas.

GET /
Endpoint de bienvenida de la API.
