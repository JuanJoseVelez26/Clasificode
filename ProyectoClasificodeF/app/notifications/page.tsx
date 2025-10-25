export default function NotificationsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Notificaciones</h1>
      <div className="bg-white p-6 rounded-lg shadow">
        <p className="text-gray-600">
          No tienes notificaciones nuevas.
        </p>
        {/* Aquí se listarán las notificaciones */}
      </div>
    </div>
  );
}
