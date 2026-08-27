using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Threading;
using System.Windows.Forms;

namespace AcademicDesignWorkflow.AxMath
{
    [StructLayout(LayoutKind.Sequential)]
    public struct OleRect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct SizeL
    {
        public int Cx;
        public int Cy;
    }

    [ComImport]
    [Guid("00000112-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IOleObject
    {
        [PreserveSig] int SetClientSite([MarshalAs(UnmanagedType.Interface)] IOleClientSite site);
        [PreserveSig] int GetClientSite([MarshalAs(UnmanagedType.Interface)] out IOleClientSite site);
        [PreserveSig] int SetHostNames([MarshalAs(UnmanagedType.LPWStr)] string containerApp, [MarshalAs(UnmanagedType.LPWStr)] string containerObj);
        [PreserveSig] int Close(uint saveOption);
        [PreserveSig] int SetMoniker(uint whichMoniker, [MarshalAs(UnmanagedType.Interface)] object moniker);
        [PreserveSig] int GetMoniker(uint assign, uint whichMoniker, [MarshalAs(UnmanagedType.Interface)] out object moniker);
        [PreserveSig] int InitFromData([MarshalAs(UnmanagedType.Interface)] object dataObject, bool creation, uint reserved);
        [PreserveSig] int GetClipboardData(uint reserved, [MarshalAs(UnmanagedType.Interface)] out object dataObject);
        [PreserveSig] int DoVerb(int verb, IntPtr message, [MarshalAs(UnmanagedType.Interface)] IOleClientSite activeSite, int index, IntPtr parentWindow, ref OleRect position);
        [PreserveSig] int EnumVerbs(out IntPtr enumOleVerb);
        [PreserveSig] int Update();
        [PreserveSig] int IsUpToDate();
        [PreserveSig] int GetUserClassID(out Guid classId);
        [PreserveSig] int GetUserType(uint formOfType, out IntPtr userType);
        [PreserveSig] int SetExtent(uint drawAspect, ref SizeL size);
        [PreserveSig] int GetExtent(uint drawAspect, out SizeL size);
        [PreserveSig] int Advise(IntPtr adviseSink, out uint connection);
        [PreserveSig] int Unadvise(uint connection);
        [PreserveSig] int EnumAdvise(out IntPtr enumStatData);
        [PreserveSig] int GetMiscStatus(uint aspect, out uint status);
        [PreserveSig] int SetColorScheme(IntPtr logPalette);
    }

    [ComImport]
    [Guid("00000118-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IOleClientSite
    {
        [PreserveSig] int SaveObject();
        [PreserveSig] int GetMoniker(uint assign, uint whichMoniker, out IntPtr moniker);
        [PreserveSig] int GetContainer(out IntPtr container);
        [PreserveSig] int ShowObject();
        [PreserveSig] int OnShowWindow(bool show);
        [PreserveSig] int RequestNewObjectLayout();
    }

    [ComImport]
    [Guid("0000010A-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPersistStorage
    {
        void GetClassID(out Guid classId);
        [PreserveSig] int IsDirty();
        void InitNew([MarshalAs(UnmanagedType.Interface)] IStorage storage);
        void Load([MarshalAs(UnmanagedType.Interface)] IStorage storage);
        void Save([MarshalAs(UnmanagedType.Interface)] IStorage storage, [MarshalAs(UnmanagedType.Bool)] bool sameAsLoad);
        void SaveCompleted([MarshalAs(UnmanagedType.Interface)] IStorage storage);
        void HandsOffStorage();
    }

    [ComImport]
    [Guid("0000000B-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IStorage
    {
        void CreateStream([MarshalAs(UnmanagedType.LPWStr)] string name, uint mode, uint reserved1, uint reserved2, out IStream stream);
        void OpenStream([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr reserved1, uint mode, uint reserved2, out IStream stream);
        void CreateStorage([MarshalAs(UnmanagedType.LPWStr)] string name, uint mode, uint reserved1, uint reserved2, out IStorage storage);
        void OpenStorage([MarshalAs(UnmanagedType.LPWStr)] string name, IStorage priority, uint mode, IntPtr exclude, uint reserved, out IStorage storage);
        void CopyTo(uint ciidExclude, IntPtr iidExclude, IntPtr exclude, IStorage destination);
        void MoveElementTo([MarshalAs(UnmanagedType.LPWStr)] string name, IStorage destination, [MarshalAs(UnmanagedType.LPWStr)] string newName, uint flags);
        void Commit(uint flags);
        void Revert();
        void EnumElements(uint reserved1, IntPtr reserved2, uint reserved3, out IntPtr enumerator);
        void DestroyElement([MarshalAs(UnmanagedType.LPWStr)] string name);
        void RenameElement([MarshalAs(UnmanagedType.LPWStr)] string oldName, [MarshalAs(UnmanagedType.LPWStr)] string newName);
        void SetElementTimes([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr creation, IntPtr access, IntPtr modification);
        void SetClass(ref Guid classId);
        void SetStateBits(uint stateBits, uint mask);
        void Stat(out System.Runtime.InteropServices.ComTypes.STATSTG stat, uint flags);
    }

    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.None)]
    public sealed class ClientSite : IOleClientSite
    {
        private IOleObject oleObject;
        private IStorage storage;
        public int SaveCount { get; private set; }
        public string LastSaveError { get; private set; }

        public void Attach(IOleObject value, IStorage targetStorage)
        {
            oleObject = value;
            storage = targetStorage;
        }

        public int SaveObject()
        {
            SaveCount++;
            try
            {
                IPersistStorage persist = (IPersistStorage)oleObject;
                persist.Save(storage, true);
                persist.SaveCompleted(storage);
                storage.Commit(0);
                return 0;
            }
            catch (Exception error)
            {
                LastSaveError = error.ToString();
                return Marshal.GetHRForException(error);
            }
        }

        public int GetMoniker(uint assign, uint whichMoniker, out IntPtr moniker) { moniker = IntPtr.Zero; return unchecked((int)0x80004001); }
        public int GetContainer(out IntPtr container) { container = IntPtr.Zero; return unchecked((int)0x80004002); }
        public int ShowObject() { return 0; }
        public int OnShowWindow(bool show) { return 0; }
        public int RequestNewObjectLayout() { return unchecked((int)0x80004001); }
    }

    internal static class NativeMethods
    {
        [DllImport("ole32.dll")]
        internal static extern int OleInitialize(IntPtr reserved);

        [DllImport("ole32.dll")]
        internal static extern void OleUninitialize();

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        internal static extern int StgCreateDocfile(string name, uint mode, uint reserved, out IStorage storage);

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        internal static extern int StgOpenStorage(string name, IStorage priority, uint mode, IntPtr exclude, uint reserved, out IStorage storage);

        [DllImport("ole32.dll")]
        internal static extern int OleCreate(ref Guid classId, ref Guid interfaceId, uint renderOption, IntPtr formatEtc, [MarshalAs(UnmanagedType.Interface)] IOleClientSite clientSite, [MarshalAs(UnmanagedType.Interface)] IStorage storage, [MarshalAs(UnmanagedType.Interface)] out IOleObject oleObject);

        [DllImport("ole32.dll")]
        internal static extern int OleLoad([MarshalAs(UnmanagedType.Interface)] IStorage storage, ref Guid interfaceId, [MarshalAs(UnmanagedType.Interface)] IOleClientSite clientSite, [MarshalAs(UnmanagedType.Interface)] out IOleObject oleObject);

        [DllImport("ole32.dll")]
        internal static extern int OleRun([MarshalAs(UnmanagedType.IUnknown)] object unknown);

        [DllImport("ole32.dll")]
        internal static extern int OleSetContainedObject([MarshalAs(UnmanagedType.IUnknown)] object unknown, bool contained);

        [DllImport("ole32.dll")]
        internal static extern int WriteClassStg([MarshalAs(UnmanagedType.Interface)] IStorage storage, ref Guid classId);
    }

    internal static class Program
    {
        private const uint StgmReadWrite = 0x00000002;
        private const uint StgmShareExclusive = 0x00000010;
        private const uint StgmCreate = 0x00001000;
        private const uint OleRenderDraw = 1;
        private const uint OleCloseSaveIfDirty = 0;
        private static readonly Guid AxMathClassId = new Guid("B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28");
        private static readonly Guid OleObjectInterfaceId = new Guid("00000112-0000-0000-C000-000000000046");

        private static void Check(int result, string operation)
        {
            if (result < 0) Marshal.ThrowExceptionForHR(result, new IntPtr(-1));
            Console.WriteLine(operation + "=0x" + result.ToString("X8"));
        }

        [STAThread]
        private static int Main(string[] args)
        {
            bool editExisting = args.Length == 3 && args[0] == "--edit";
            if (args.Length != 2 && !editExisting)
            {
                Console.Error.WriteLine("Usage: AxMathOleDirect.exe OUTPUT_STORAGE LATEX | --edit EXISTING_STORAGE LATEX");
                return 2;
            }

            string outputPath = Path.GetFullPath(editExisting ? args[1] : args[0]);
            string latex = editExisting ? args[2] : args[1];
            if (!editExisting && File.Exists(outputPath))
            {
                Console.Error.WriteLine("Refusing to overwrite: " + outputPath);
                return 3;
            }
            if (editExisting && !File.Exists(outputPath))
            {
                Console.Error.WriteLine("Missing storage to edit: " + outputPath);
                return 3;
            }

            IOleObject oleObject = null;
            IStorage storage = null;
            ClientSite clientSite = null;
            int oleInit = NativeMethods.OleInitialize(IntPtr.Zero);
            if (oleInit < 0) Marshal.ThrowExceptionForHR(oleInit);

            try
            {
                Guid classId = AxMathClassId;
                Guid interfaceId = OleObjectInterfaceId;
                clientSite = new ClientSite();
                if (editExisting)
                {
                    Check(NativeMethods.StgOpenStorage(outputPath, null, StgmReadWrite | StgmShareExclusive, IntPtr.Zero, 0, out storage), "StgOpenStorage");
                    Check(NativeMethods.OleLoad(storage, ref interfaceId, clientSite, out oleObject), "OleLoad");
                }
                else
                {
                    Check(NativeMethods.StgCreateDocfile(outputPath, StgmCreate | StgmReadWrite | StgmShareExclusive, 0, out storage), "StgCreateDocfile");
                    Check(NativeMethods.WriteClassStg(storage, ref classId), "WriteClassStg");
                    Check(NativeMethods.OleCreate(ref classId, ref interfaceId, OleRenderDraw, IntPtr.Zero, clientSite, storage, out oleObject), "OleCreate");
                }
                clientSite.Attach(oleObject, storage);
                Check(NativeMethods.OleSetContainedObject(oleObject, true), "OleSetContainedObject");
                Check(NativeMethods.OleRun(oleObject), "OleRun");
                Check(oleObject.SetHostNames("Visio", "Academic equation"), "SetHostNames");

                Clipboard.SetText(latex, TextDataFormat.UnicodeText);
                OleRect rect = new OleRect { Left = 0, Top = 0, Right = 1200, Bottom = 300 };
                Check(oleObject.DoVerb(11, IntPtr.Zero, clientSite, 0, IntPtr.Zero, ref rect), "DoVerbPasteLatex");
                Thread.Sleep(500);
                Console.WriteLine("ClientSiteSaveCount=" + clientSite.SaveCount);
                Console.WriteLine("ClientSiteSaveError=" + (clientSite.LastSaveError ?? string.Empty));
                storage.Commit(0);
                Console.WriteLine("StorageCommit=0x00000000");

                try { Check(oleObject.Close(OleCloseSaveIfDirty), "OleClose"); }
                catch (COMException error) { Console.WriteLine("OleCloseDisconnected=" + error.ErrorCode.ToString("X8")); }
                return clientSite.SaveCount > 0 && string.IsNullOrEmpty(clientSite.LastSaveError) ? 0 : 4;
            }
            catch (Exception error)
            {
                Console.Error.WriteLine(error.ToString());
                return 1;
            }
            finally
            {
                if (oleObject != null) Marshal.FinalReleaseComObject(oleObject);
                if (storage != null) Marshal.FinalReleaseComObject(storage);
                NativeMethods.OleUninitialize();
            }
        }
    }
}
