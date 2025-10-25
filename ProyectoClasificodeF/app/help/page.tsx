export default function HelpPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Ayuda y Soporte</h1>
      <div className="bg-white p-6 rounded-lg shadow space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Preguntas Frecuentes</h2>
          <p className="text-gray-600 mt-2">
            Encuentra respuestas a las preguntas más comunes sobre el uso de la plataforma.
          </p>
        </div>
        
        <div>
          <h2 className="text-lg font-semibold">Contacto de Soporte</h2>
          <p className="text-gray-600 mt-2">
            ¿Necesitas ayuda? Contáctanos a soporte@clasificode.com
          </p>
        </div>
      </div>
    </div>
  );
}
